"""Real API + LangGraph + SQLite + semantic/PDF engines; model responses are fixtures."""

import json
from io import BytesIO
from docx import Document
from pathlib import Path
import shutil

from fastapi.testclient import TestClient
import httpx
import pytest
from sqlmodel import Session, select

from app.config import Settings
from app.db import get_session, init_db, make_engine
from app.models import Application, UserAction, utcnow
from app.query_parser import QuerySpec
from app.resumes import SelectedStatement, ResumeExtraction, grounded_facts, read_upload, resume_statements

SOURCE=(Path(__file__).parent/'fixtures/fictional-resume.tex').read_text()
RAW,_=read_upload('fixture.tex',SOURCE.encode())
SELECTIONS=[('project','Built Java payment APIs using Spring Boot.'),('project','Built Python analytics dashboards using SQL.'),('experience','Implemented unit tests for both projects.'),('skill','Java, Python, SQL.')]
EXTRACTION=ResumeExtraction(facts=[SelectedStatement(category=category,statement_id=next(s['id'] for s in resume_statements(RAW) if evidence in s['text'])) for category,evidence in SELECTIONS])
FACTS=grounded_facts(EXTRACTION,RAW)
JAVA,PYTHON=FACTS['facts'][:2]


def resume_docx(text=RAW):
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    return output.getvalue()


@pytest.fixture
def client(monkeypatch,tmp_path):
    import app.main as main
    import app.orchestrator as orchestrator
    import app.resumes as resumes
    import app.tailoring as tailoring
    import app.curator as curator
    import app.research as research
    import app.search_context as context
    from app.llm import call_tool
    engine=make_engine(f'sqlite:///{tmp_path}/test.db');init_db(engine)
    def sessions():
        with Session(engine) as session: yield session
    main.app.dependency_overrides[get_session]=sessions
    settings=Settings(openrouter_api_key='fixture-key',openrouter_model='fixture/tool-model:free',artifact_dir=str(tmp_path/'artifacts'))
    monkeypatch.setattr(main,'settings',settings)
    monkeypatch.setattr(orchestrator,'get_settings',lambda:settings)
    monkeypatch.setattr(main,'init_db',lambda:None)
    monkeypatch.setattr(curator,'get_settings',lambda:settings)
    async def query(q):
        return QuerySpec(hard_filters={'recency_days':7},soft_preferences=[{'factor':'resume_match','weight':1.0,'evidence':'my resume','targets':[]}])
    async def discover(*a,**kw):
        candidates=[{'title':'Java backend engineer','company':'Fictional Test Co','url':'https://example.org/java','location':'Remote','description':'Java payment APIs Spring Boot','description_snippet':'Java payment APIs','age_days':2,'posted_at':utcnow().isoformat(),'source':'bs4'},
                    {'title':'Python analytics engineer','company':'Fictional Test Co','url':'https://example.org/python','location':'Remote','description':'Python analytics dashboards SQL','description_snippet':'Python analytics dashboards','age_days':2,'posted_at':utcnow().isoformat(),'source':'bs4'}]
        return {'jobs':[j for j in candidates if j['url'] not in kw.get('tracked_urls',set())],'warnings':[]}
    def handler(request):
        payload=json.loads(request.content)
        assert payload['provider']['data_collection']=='deny'
        assert payload['provider']['max_price']=={'prompt':0,'completion':0,'request':0}
        name=payload['tool_choice']['function']['name']
        data=json.loads(payload['messages'][1]['content'])
        if name=='emit_resumeextraction':
            output={'facts':[{'category':category,'statement_id':next(s['id'] for s in data['statements'] if evidence in s['text'])} for category,evidence in SELECTIONS]}
        elif name=='emit_tailoreddraft':
            fact=JAVA if 'Java' in data['job']['title'] else PYTHON
            claim={'text':fact['text'],'fact_ids':[fact['id']]}
            output={'bullets':[claim],'cover_letter_claims':[claim]}
        elif name=='emit_criticresponse':
            output={'checks':[{'claim_index':c['index'],'supported':True,'reason':'Exact source fact'} for c in data['claims']]}
        elif name=='emit_curationplan':
            fact=JAVA if 'Java' in data['job']['title'] else PYTHON
            target=next(s for s in data['statements'] if s['kind']=='bullet' and s['text']!=fact['text'])
            output={'edits':[{'statement_id':target['id'],'text':fact['text'],'fact_ids':[fact['id']]}]}
        else:
            raise AssertionError(name)
        return httpx.Response(200,json={'choices':[{'message':{'tool_calls':[{'function':{'name':name,'arguments':json.dumps(output)}}]}}]})
    async def tool(schema,**kwargs):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as active:
            return await call_tool(schema,**kwargs,settings=settings,client=active)
    for module in (resumes,tailoring,curator,research): monkeypatch.setattr(module,'call_tool',tool)
    monkeypatch.setattr(orchestrator,'parse_query',query)
    async def resolve(*args, **kwargs):
        return context.IntentResolution(kind='new')
    monkeypatch.setattr(context, 'call_tool', resolve)
    monkeypatch.setattr(orchestrator,'discover_jobs',discover)
    async def no_sources(company): return []
    monkeypatch.setattr(research,'gather_sources',no_sources)
    with TestClient(main.app) as active:
        yield active,engine,tmp_path
    main.app.dependency_overrides.clear()


def test_phase1_full_api_graph_loop_and_reload_persistence(client):
    client,engine,_=client
    # Resume is optional for search.
    result=client.post('/api/search',json={'query':'jobs matching my resume','mode':'natural'}).json()
    assert result['trace']==['query_parser','scout','ranking'] and len(result['jobs'])==2
    assert all(j['status']=='discovered' for j in result['jobs'])
    assert client.get('/api/jobs').json() == []
    response=client.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    assert response.status_code==200,response.text
    for job in result['jobs']:
        assert client.post(f"/api/jobs/{job['id']}/interest", json={'turn_id':result['turn_id']}).status_code==200
    jobs=client.get('/api/jobs').json()
    first=client.post(f"/api/jobs/{jobs[0]['id']}/tailor")
    second=client.post(f"/api/jobs/{jobs[1]['id']}/tailor")
    assert first.status_code==second.status_code==200,(first.text,second.text)
    assert first.json()['draft']!=second.json()['draft']
    assert first.json()['trace']==['tailor','critic'] and first.json()['critique']['passed']
    assert first.json()['critique']['content_match']['evidence']
    assert abs(first.json()['critique']['content_match']['adjustment_points'])<=10
    job_id=jobs[0]['id']
    assert client.patch(f'/api/jobs/{job_id}/status',json={'status':'applied'}).status_code==422
    assert client.post(f'/api/jobs/{job_id}/mark-applied',json={'explicit_action':False}).status_code==422
    assert client.post(f'/api/jobs/{job_id}/mark-applied',json={'explicit_action':'true'}).status_code==422
    approved=client.post(f'/api/jobs/{job_id}/mark-applied',json={'explicit_action':True})
    assert approved.status_code==200,approved.text
    assert client.get(f'/api/jobs/{job_id}').json()['status']=='applied'
    with Session(engine) as fresh:
        assert fresh.exec(select(Application).where(Application.job_id==job_id)).one().status=='applied'
        assert len(fresh.exec(select(UserAction).where(UserAction.action=='mark_applied')).all())==1
    assert client.patch(f'/api/jobs/{job_id}/status',json={'status':'interviewing'}).status_code==200
    assert client.patch(f'/api/jobs/{job_id}/status',json={'status':'resolved','outcome':'offer'}).status_code==200
    assert client.get('/api/memory').json()


@pytest.mark.skipif(not shutil.which('tectonic'),reason='Real PDF engine required')
def test_phase2_rank_curate_research_pipeline_and_artifact_download(client):
    client,engine,root=client
    assert client.post('/api/resume',files={'file':('fictional.docx',resume_docx())}).status_code==200
    # Legacy stored LaTeX profiles still retain the original layout during curation.
    from app.db import get_profile
    with Session(engine) as session:
        profile = get_profile(session)
        profile.latex_source = SOURCE
        session.add(profile)
        session.commit()
    result=client.post('/api/search',json={'query':'jobs matching my resume this week','mode':'natural'})
    assert result.status_code==200,result.text
    jobs=result.json()['jobs']
    assert len(jobs)==2 and all(j['fit_score']>0 and j['explanation'] for j in jobs)
    for job in jobs:
        assert client.post(f"/api/jobs/{job['id']}/interest", json={'turn_id':result.json()['turn_id']}).status_code==200
    outputs=[]
    for job in jobs:
        response=client.post(f"/api/jobs/{job['id']}/curate")
        assert response.status_code==200,response.text
        artifact=response.json()
        assert artifact['edit_count']==1 and artifact['original_layout_preserved']
        downloaded=client.get(artifact['pdf_url'])
        assert downloaded.content.startswith(b'%PDF')
        assert downloaded.headers['content-disposition'].startswith('inline;')
        assert client.get(artifact['tex_url']).headers['content-disposition'].startswith('attachment;')
        outputs.append(client.get(artifact['tex_url']).text)
    from test_curator import masked
    assert outputs[0]!=outputs[1] and masked(outputs[0])==masked(outputs[1])==masked(SOURCE)
    research=client.post(f"/api/jobs/{jobs[0]['id']}/research").json()
    assert research['sufficient_information'] is False and not research['rounds']
    assert 'Not enough public information' in research['difficulty_note']


def test_resume_replacement_invalidates_previous_draft(client):
    client,_,_=client
    client.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    result=client.post('/api/search',json={'query':'jobs my resume'}).json()
    job=result['jobs'][0]
    assert client.post(f"/api/jobs/{job['id']}/interest",json={'turn_id':result['turn_id']}).status_code==200
    assert client.post(f"/api/jobs/{job['id']}/tailor").status_code==200
    client.post('/api/resume',files={'file':('replacement.docx',resume_docx())})
    response=client.post(f"/api/jobs/{job['id']}/mark-applied",json={'explicit_action':True})
    assert response.status_code==422
    assert client.get(f"/api/jobs/{job['id']}").json()['fit_score'] is None


def test_local_learning_requires_explicit_boolean_opt_in(client):
    client,_,_=client
    assert not client.get('/api/personalization').json()['enabled']
    assert client.put('/api/personalization/consent',json={'enabled':'yes'}).status_code==422
    assert client.put('/api/personalization/consent',json={'enabled':True}).json()['enabled']
    assert not client.put('/api/personalization/consent',json={'enabled':False}).json()['enabled']


def test_resume_search_requires_stored_facts_before_discovery(client, monkeypatch):
    import app.orchestrator as orchestrator
    active, _, _ = client
    async def unexpected(*args, **kwargs):
        pytest.fail('Discovery and query parsing must not run without a resume')
    monkeypatch.setattr(orchestrator, 'parse_query', unexpected)
    monkeypatch.setattr(orchestrator, 'discover_jobs', unexpected)
    response = active.post('/api/search', json={'mode': 'resume'})
    assert response.status_code == 422
    assert 'Add your resume' in response.json()['detail']


def test_resume_only_search_uses_facts_without_an_llm_query_and_deduplicates(client, monkeypatch):
    import app.orchestrator as orchestrator
    from app.db import get_profile
    from app.scoring import rank_jobs
    active, engine, _ = client
    assert active.post('/api/resume', files={'file': ('fictional.docx', resume_docx())}).status_code == 200
    with Session(engine) as session:
        profile = get_profile(session)
        profile.structured_facts = {'facts': [JAVA]}
        session.add(profile)
        session.commit()
    async def unexpected(query):
        pytest.fail('An empty resume search must not call the LLM query parser')
    monkeypatch.setattr(orchestrator, 'parse_query', unexpected)
    def semantic(resume, jd):
        assert JAVA['text'] in resume
        return .9 if 'Java' in jd else .1
    monkeypatch.setattr(orchestrator, 'rank_jobs', lambda *a, **kw: rank_jobs(*a, semantic=semantic, **kw))
    response = active.post('/api/search', json={'mode': 'resume', 'query': '   '})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['trace'] == ['resume_search', 'scout', 'ranking']
    assert result['query_spec'] == QuerySpec(hard_filters={}, soft_preferences=[]).model_dump()
    assert [j['fit_score'] for j in result['jobs']] == [90, 10]
    assert result['jobs'][0]['title'] == 'Java backend engineer'
    assert all(j['status'] == 'discovered' for j in result['jobs'])
    assert active.get('/api/jobs').json() == []
    # Discovery may repeat across chat turns until the user chooses interest.
    assert len(active.post('/api/search', json={'mode': 'resume'}).json()['jobs']) == 2
    for job in result['jobs']:
        assert active.post(f"/api/jobs/{job['id']}/interest",json={'turn_id':result['turn_id']}).status_code==200
    assert active.post('/api/search', json={'mode': 'resume'}).json()['jobs'] == []


def test_resume_query_filters_jobs_and_still_ranks_against_stored_facts(client, monkeypatch):
    import app.orchestrator as orchestrator
    active, _, _ = client
    assert active.post('/api/resume', files={'file': ('fictional.docx', resume_docx())}).status_code == 200
    async def query(text):
        assert text == 'Python jobs'
        return QuerySpec(hard_filters={'tech_stack_keywords': ['python']}, soft_preferences=[])
    monkeypatch.setattr(orchestrator, 'parse_query', query)
    response = active.post('/api/search', json={'mode': 'resume', 'query': 'Python jobs'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['jobs']) == 1
    assert result['jobs'][0]['title'] == 'Python analytics engineer'
    assert result['jobs'][0]['scoring_signals']['resume_match'] > 0
    assert 'stored resume facts' in result['jobs'][0]['explanation']
