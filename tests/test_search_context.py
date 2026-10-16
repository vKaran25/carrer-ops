"""Isolated structured-memory acceptance; all model responses are fixtures."""
import asyncio

import pytest
from sqlmodel import Session

from app.db import init_db, make_engine
from app.llm import LLMError
from app.models import User
from app.query_parser import QuerySpec, QueryParserError
from app import search_context as memory
from test_workflows import client, resume_docx


def spec(hard=None, soft=None, scope=None):
    return QuerySpec(hard_filters=hard or {}, soft_preferences=soft or [], location_scope=scope)


@pytest.fixture
def session(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/memory.db')
    init_db(engine)
    with Session(engine) as active:
        active.add(User(id=2))
        active.commit()
        yield active
    engine.dispose()


def classifier(monkeypatch, kind='follow_up', clears=None):
    async def tool(*_, **kwargs):
        assert 'resume' not in kwargs['data'] and 'history' not in kwargs['data']
        return memory.IntentResolution(kind=kind, clear_fields=clears or [])
    monkeypatch.setattr(memory, 'call_tool', tool)


def prepare(session, query, patch, user_id=1):
    async def parse(_):
        return patch
    return asyncio.run(memory.prepare(session, user_id, query, parse))


def commit(session, prepared, user_id=1):
    assert memory.commit_success(session, user_id, prepared['context_update'], 'fixture-digest', 123)
    session.commit()


def test_followup_overrides_same_field_and_new_intent_drops_old_constraints(session, monkeypatch):
    classifier(monkeypatch, 'new')
    first = prepare(session, 'Python backend jobs in India', spec({'tech_stack_keywords':['python'], 'role_keywords':['backend'], 'locations':['India']}))
    assert not memory.view(session,1,None)['active']  # preparation does not save intent
    commit(session, first)
    classifier(monkeypatch)
    follow = prepare(session, 'same role but in Delhi', spec({'locations':['Delhi']}))
    hard = follow['query_spec']['hard_filters']
    assert hard['tech_stack_keywords'] == ['python'] and hard['role_keywords'] == ['backend'] and hard['locations'] == ['Delhi']
    commit(session, follow)
    classifier(monkeypatch, 'new')
    new = prepare(session, 'Find React jobs', spec({'tech_stack_keywords':['react']}))
    assert new['query_spec']['hard_filters']['locations'] == []
    assert new['query_spec']['hard_filters']['tech_stack_keywords'] == ['react']


def test_explicit_defaults_override_remove_and_blank_resume_search(session, monkeypatch):
    defaults = spec({'locations':['India'], 'recency_days':7})
    memory.save_preferences(session,1,'Jobs in India posted this week',defaults)
    classifier(monkeypatch, 'new')
    current = prepare(session,'Python jobs in Canada',spec({'tech_stack_keywords':['python'],'locations':['Canada']}))
    assert current['query_spec']['hard_filters']['locations'] == ['Canada']
    assert current['query_spec']['hard_filters']['recency_days'] == 7
    commit(session,current)
    classifier(monkeypatch, clears=[{'field':'locations','evidence':'anywhere'},{'field':'location_scope','evidence':'anywhere'}])
    cleared = prepare(session,'same role anywhere',spec())
    assert cleared['query_spec']['hard_filters']['locations'] == []
    commit(session,cleared)
    classifier(monkeypatch)
    again = prepare(session,'same jobs',spec())
    assert again['query_spec']['hard_filters']['locations'] == []  # saved India cannot reappear
    blank = prepare(session,'',spec())
    assert blank['query_spec']['hard_filters']['locations'] == ['India']
    assert blank['query_spec']['hard_filters']['tech_stack_keywords'] == []
    memory.save_preferences(session,1,'',None)
    assert memory.view(session,1,None)['preferences'] is None


def test_reset_keeps_defaults_and_blocks_stale_inflight_context(session, monkeypatch):
    memory.save_preferences(session,1,'India',spec({'locations':['India']}))
    classifier(monkeypatch,'new')
    pending = prepare(session,'Python jobs',spec({'tech_stack_keywords':['python']}))
    memory.reset(session,1)
    assert not memory.commit_success(session,1,pending['context_update'],None,1)
    session.commit()
    state = memory.view(session,1,None)
    assert not state['active'] and state['preferences']['query'] == 'India'
    classifier(monkeypatch)
    with pytest.raises(ValueError,match='previous role'):
        prepare(session,'same role',spec())


def test_preference_edit_invalidates_older_run_and_user_records_are_isolated(session, monkeypatch):
    classifier(monkeypatch,'new')
    old = prepare(session,'Python roles',spec({'tech_stack_keywords':['python']}))
    memory.save_preferences(session,1,'Canada',spec({'locations':['Canada']}))
    assert not memory.commit_success(session,1,old['context_update'],None,1)
    session.commit()
    other = prepare(session,'React jobs',spec({'tech_stack_keywords':['react']}),user_id=2)
    commit(session,other,user_id=2)
    assert memory.view(session,1,None)['preferences']['query'] == 'Canada'
    assert memory.view(session,2,None)['preferences'] is None
    assert memory.view(session,2,None)['effective_spec']['hard_filters']['tech_stack_keywords'] == ['react']
    assert not memory.view(session,1,None)['active']


def test_unsupported_clear_and_clarification_never_replace_active_intent(session, monkeypatch):
    classifier(monkeypatch,'new')
    commit(session,prepare(session,'Python roles',spec({'tech_stack_keywords':['python']})))
    before = memory.view(session,1,'fixture-digest')
    classifier(monkeypatch,clears=[{'field':'tech_stack_keywords','evidence':'invented text'}])
    with pytest.raises(LLMError,match='unsupported'):
        prepare(session,'same role',spec())
    classifier(monkeypatch,'clarify')
    with pytest.raises(ValueError):
        prepare(session,'those ones',spec())
    assert memory.view(session,1,'fixture-digest') == before


def test_nearby_and_exact_city_overrides_do_not_retain_conflicting_scope():
    near = spec(scope={'place':'Fixture City','mode':'preferred','radius_km':50.,'evidence':'near Fixture City'})
    exact = spec({'locations':['Other City']})
    assert memory.merge(near,exact).location_scope is None
    assert memory.merge(exact,near).hard_filters.locations == []


def test_api_memory_success_failure_reset_and_resume_change(client, monkeypatch):
    import app.orchestrator as graph
    active, engine, _ = client
    active.post('/api/resume',files={'file':('fixture.docx',resume_docx())})
    first = active.search(json={'mode':'resume','query':'Python roles'}).json()
    assert first['context_info']['saved_as_active']
    state = active.get('/api/search/context').json()
    assert state['active'] and state['last_query'] == 'Python roles'
    async def bad(_):
        raise QueryParserError('fixture parse failed')
    monkeypatch.setattr(graph,'parse_query',bad)
    assert active.search(json={'mode':'resume','query':'a failed request'}).status_code == 503
    assert active.get('/api/search/context').json()['last_query'] == 'Python roles'
    async def failed_sources(*args,**kwargs):
        return {'jobs':[],'warnings':['All fixture sources failed'],'stats':{'retrieved':0,'sources_searched':1}}
    monkeypatch.setattr(graph,'discover_jobs',failed_sources)
    failed = active.search(json={'mode':'resume','query':''}).json()
    assert not failed['context_info']['saved_as_active']
    assert active.get('/api/search/context').json()['last_query'] == 'Python roles'
    assert active.delete('/api/resume').status_code == 200
    assert active.get('/api/search/context').json()['resume_changed']
    assert active.delete('/api/search/context').json()['active'] is False
    assert len(active.get('/api/chat').json()) == 2
    assert active.get('/api/jobs').json() == []


def test_api_preferences_are_explicit_editable_and_survive_reset(client, monkeypatch):
    import app.main as main
    active, _, _ = client
    async def parse(query):
        return spec({'locations':[query]})
    monkeypatch.setattr(main,'parse_query',parse)
    assert active.get('/api/search/context').json()['preferences'] is None
    assert active.put('/api/search/preferences',json={'query':'India'}).json()['preferences']['query'] == 'India'
    assert active.delete('/api/search/context').json()['preferences']['query'] == 'India'
    assert active.put('/api/search/preferences',json={'query':'Canada'}).json()['preferences']['query'] == 'Canada'
    assert active.put('/api/search/preferences',json={'query':'','user_id':2}).status_code == 422
    assert active.delete('/api/search/preferences').json()['preferences'] is None
