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
        from search_helpers import complete_search
        active.search = lambda **kw: complete_search(active, engine, **kw)
        yield active,engine,tmp_path
    main.app.dependency_overrides.clear()


def test_phase1_full_api_graph_loop_and_reload_persistence(client):
    client,engine,_=client
    assert client.post('/api/resume',files={'file':('fictional.docx',resume_docx())}).status_code==200
    result=client.search(json={'query':'jobs matching my resume','mode':'natural'}).json()
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
    assert first.status_code==second.status_code==404
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


def test_deferred_preparation_api_is_unavailable_in_core(client):
    active,_,_=client
    active.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    result=active.search(json={'mode':'resume'}).json()
    job=result['jobs'][0]
    active.post(f"/api/jobs/{job['id']}/interest",json={'turn_id':result['turn_id']})
    for action in ('tailor','curate','research'):
        assert active.post(f"/api/jobs/{job['id']}/{action}").status_code==404

def test_resume_replacement_invalidates_previous_draft(client):
    client,engine,_=client
    client.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    result=client.search(json={'query':'jobs my resume'}).json()
    job=result['jobs'][0]
    assert client.post(f"/api/jobs/{job['id']}/interest",json={'turn_id':result['turn_id']}).status_code==200
    with Session(engine) as session:
        application=session.exec(select(Application).where(Application.job_id==job['id'])).one()
        application.draft={'legacy':'fictional preserved artifact'}
        session.add(application);session.commit()
    client.post('/api/resume',files={'file':('replacement.docx',resume_docx())})
    assert client.get(f"/api/jobs/{job['id']}").json()['fit_score'] is None
    assert client.post(f"/api/jobs/{job['id']}/mark-applied",json={'explicit_action':True}).status_code==200

def test_local_learning_is_unavailable_in_core(client):
    client,_,_=client
    assert client.get('/api/personalization').status_code==404
    for enabled in (True,False,'yes'):
        assert client.put('/api/personalization/consent',json={'enabled':enabled}).status_code==404

def test_resume_search_requires_stored_facts_before_discovery(client, monkeypatch):
    import app.orchestrator as orchestrator
    active, _, _ = client
    async def unexpected(*args, **kwargs):
        pytest.fail('Discovery and query parsing must not run without a resume')
    monkeypatch.setattr(orchestrator, 'parse_query', unexpected)
    monkeypatch.setattr(orchestrator, 'discover_jobs', unexpected)
    response = active.search( json={'mode': 'resume'})
    assert response.status_code == 422
    assert 'resume' in response.json()['detail'].lower()


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
    response = active.search( json={'mode': 'resume', 'query': '   '})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['trace'] == ['resume_search', 'scout', 'ranking']
    assert result['query_spec'] == QuerySpec(hard_filters={}, soft_preferences=[]).model_dump()
    assert [j['fit_score'] for j in result['jobs']] == [90, 10]
    assert result['jobs'][0]['title'] == 'Java backend engineer'
    assert all(j['status'] == 'discovered' for j in result['jobs'])
    assert active.get('/api/jobs').json() == []
    # Discovery may repeat across chat turns until the user chooses interest.
    assert len(active.search( json={'mode': 'resume'}).json()['jobs']) == 2
    for job in result['jobs']:
        assert active.post(f"/api/jobs/{job['id']}/interest",json={'turn_id':result['turn_id']}).status_code==200
    assert active.search( json={'mode': 'resume'}).json()['jobs'] == []


def test_resume_query_filters_jobs_and_still_ranks_against_stored_facts(client, monkeypatch):
    import app.orchestrator as orchestrator
    active, _, _ = client
    assert active.post('/api/resume', files={'file': ('fictional.docx', resume_docx())}).status_code == 200
    async def query(text):
        assert text == 'Python jobs'
        return QuerySpec(hard_filters={'tech_stack_keywords': ['python']}, soft_preferences=[])
    monkeypatch.setattr(orchestrator, 'parse_query', query)
    response = active.search( json={'mode': 'resume', 'query': 'Python jobs'})
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result['jobs']) == 1
    assert result['jobs'][0]['title'] == 'Python analytics engineer'
    assert result['jobs'][0]['scoring_signals']['resume_match'] > 0
    assert 'stored resume facts' in result['jobs'][0]['explanation']
