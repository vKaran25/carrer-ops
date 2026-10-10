"""Real API + LangGraph + SQLite + semantic/PDF engines; model responses are fixtures."""

import json
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
from app.resumes import ExtractedFact, ResumeExtraction, grounded_facts, read_upload

SOURCE=(Path(__file__).parent/'fixtures/fictional-resume.tex').read_text()
RAW,_=read_upload('fixture.tex',SOURCE.encode())
EXTRACTION=ResumeExtraction(facts=[ExtractedFact(category='project',evidence='Built Java payment APIs using Spring Boot.'),ExtractedFact(category='project',evidence='Built Python analytics dashboards using SQL.'),ExtractedFact(category='experience',evidence='Implemented unit tests for both projects.'),ExtractedFact(category='skill',evidence='Java, Python, SQL.')])
FACTS=grounded_facts(EXTRACTION,RAW)
JAVA,PYTHON=FACTS['facts'][:2]


@pytest.fixture
def client(monkeypatch,tmp_path):
    import app.main as main
    import app.orchestrator as orchestrator
    import app.resumes as resumes
    import app.tailoring as tailoring
    import app.curator as curator
    import app.research as research
    from app.llm import call_tool
    engine=make_engine(f'sqlite:///{tmp_path}/test.db');init_db(engine)
    def sessions():
        with Session(engine) as session: yield session
    main.app.dependency_overrides[get_session]=sessions
    settings=Settings(openrouter_api_key='fixture-key',openrouter_model='fixture/tool-model:free',artifact_dir=str(tmp_path/'artifacts'))
    monkeypatch.setattr(main,'settings',settings)
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
            output=EXTRACTION.model_dump()
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
    assert all(j['status']=='found' for j in result['jobs'])
    response=client.post('/api/resume',files={'file':('fictional.tex',SOURCE.encode(),'application/x-tex')})
    assert response.status_code==200,response.text
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
    client,_,root=client
    assert client.post('/api/resume',files={'file':('fictional.tex',SOURCE.encode())}).status_code==200
    result=client.post('/api/search',json={'query':'jobs matching my resume this week','mode':'natural'})
    assert result.status_code==200,result.text
    jobs=result.json()['jobs']
    assert len(jobs)==2 and all(j['fit_score']>0 and j['explanation'] for j in jobs)
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
    client.post('/api/resume',files={'file':('fictional.tex',SOURCE.encode())})
    job=client.post('/api/search',json={'query':'jobs my resume'}).json()['jobs'][0]
    assert client.post(f"/api/jobs/{job['id']}/tailor").status_code==200
    client.post('/api/resume',files={'file':('replacement.tex',SOURCE.encode())})
    response=client.post(f"/api/jobs/{job['id']}/mark-applied",json={'explicit_action':True})
    assert response.status_code==422
    assert client.get(f"/api/jobs/{job['id']}").json()['fit_score'] is None


def test_local_learning_requires_explicit_boolean_opt_in(client):
    client,_,_=client
    assert not client.get('/api/personalization').json()['enabled']
    assert client.put('/api/personalization/consent',json={'enabled':'yes'}).status_code==422
    assert client.put('/api/personalization/consent',json={'enabled':True}).json()['enabled']
    assert not client.put('/api/personalization/consent',json={'enabled':False}).json()['enabled']
