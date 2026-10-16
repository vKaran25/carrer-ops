"""Chat discovery, explicit tracker intake, history and approved data migration."""
from sqlmodel import Session, select

from app.db import init_db, make_engine
from app.models import Application, ChatTurn, JobPosting, UserAction
from app.tracker import approval_gate, save_jobs, save_discovered_jobs
from test_workflows import client, SOURCE, resume_docx
from app.resumes import latex_text


def test_chat_history_survives_sessions_and_discovery_cannot_prepare_or_apply(client):
    active, engine, _ = client
    assert active.post('/api/resume', files={'file':('fictional.docx',resume_docx())}).status_code == 200
    result = active.search( json={'mode':'resume'}).json()
    job_id = result['jobs'][0]['id']
    assert active.get('/api/jobs').json() == []
    assert all(n == 0 for n in active.get('/api/bootstrap').json()['counts'].values())
    with Session(engine) as fresh:
        assert len(fresh.exec(select(ChatTurn)).all()) == 1
        assert fresh.exec(select(Application)).all() == []
    saved = active.get('/api/chat').json()
    assert saved[0]['id'] == result['turn_id']
    assert saved[0]['result']['jobs'][0]['id'] == job_id
    for action in ('tailor','curate','research','mark-applied'):
        body = {'explicit_action':True} if action == 'mark-applied' else None
        assert active.post(f'/api/jobs/{job_id}/{action}',json=body).status_code == 404
    assert active.post(f'/api/jobs/{job_id}/interest',json={'turn_id':9999}).status_code == 404
    assert active.get('/api/jobs').json() == []
    selected = active.post(f'/api/jobs/{job_id}/interest',json={'turn_id':result['turn_id']})
    assert selected.status_code == 200 and selected.json()['status'] == 'interested'
    assert selected.json()['applied_at'] is None
    assert active.get('/api/chat').json()[0]['result']['jobs'][0]['status'] == 'interested'
    assert active.get('/api/bootstrap').json()['counts']['interested'] == 1
    assert active.post(f'/api/jobs/{job_id}/interest',json={'turn_id':result['turn_id']}).json() == selected.json()
    assert active.post(f'/api/jobs/{job_id}/tailor').status_code == 404
    assert active.post(f'/api/jobs/{job_id}/interest',json={'turn_id':result['turn_id']}).json()['status'] == 'interested'
    with Session(engine) as fresh:
        assert len(fresh.exec(select(Application)).all()) == 1
        assert len(fresh.exec(select(UserAction).where(UserAction.action == 'mark_interested')).all()) == 1


def test_changed_resume_preserves_history_without_reusing_old_fit(client):
    active, _, _ = client
    active.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    result = active.search(json={'mode':'resume'}).json()
    assert result['jobs'][0]['fit_score'] > 0
    assert result['jobs'][0]['score_breakdown']['components']
    assert active.get('/api/chat').json()[0]['result']['jobs'][0]['score_breakdown'] == result['jobs'][0]['score_breakdown']
    changed = SOURCE.replace('Projects','Selected projects')
    assert active.post('/api/resume',files={'file':('replacement.docx',resume_docx(latex_text(changed)))}).status_code == 200
    history = active.get('/api/chat').json()
    assert history[0]['resume_changed'] is True
    assert len(history[0]['result']['jobs']) == 2
    assert all(j['fit_score'] is None for j in history[0]['result']['jobs'])
    assert all(j['score_breakdown'] is None and j['factors'] == [] and j['scoring_signals'] == {} for j in history[0]['result']['jobs'])
    job_id = result['jobs'][0]['id']
    selected = active.post(f'/api/jobs/{job_id}/interest',json={'turn_id':result['turn_id']}).json()
    assert selected['fit_score'] is None and selected['scoring_signals'] == {}
    assert 'Resume changed' in selected['explanation']


def test_interest_must_reference_a_job_in_its_search_turn(client):
    active, engine, _ = client
    active.post('/api/resume',files={'file':('fictional.docx',resume_docx())})
    result = active.search(json={'mode':'resume','limit':1}).json()
    with Session(engine) as session:
        other = save_discovered_jobs(session,[{'title':'Other fictional role','company':'Fixture','url':'https://example.org/other'}])[0]
        other_id = other.id
    assert active.post(f'/api/jobs/{other_id}/interest',json={'turn_id':result['turn_id']}).status_code == 404
    assert active.get('/api/jobs').json() == []


def test_found_migration_is_idempotent_and_preserves_later_stages(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path}/legacy.db')
    init_db(engine)
    with Session(engine) as session:
        records = save_jobs(session,[{'title':str(i),'company':'Fictional fixture','url':f'https://example.org/{i}'} for i in range(3)])
        applications = [session.exec(select(Application).where(Application.job_id == j.id)).one() for j in records]
        applications[0].status = 'found'
        applications[0].fit_score = 71
        applications[1].status = 'tailored'
        applications[1].draft = {'fixture':'existing draft'}
        session.add_all(applications)
        session.commit()
        applied = approval_gate(session, records[2].id, explicit_action=True)
        timestamp = applied.applied_at
    init_db(engine)
    init_db(engine)
    with Session(engine) as fresh:
        rows = fresh.exec(select(Application).order_by(Application.id)).all()
        assert [a.status for a in rows] == ['interested','interested','applied']
        assert rows[0].fit_score == 71 and rows[1].draft == {'fixture':'existing draft'}
        assert rows[2].applied_at == timestamp
        audits = fresh.exec(select(UserAction).where(UserAction.action == 'migrate_found_to_interested')).all()
        assert len(audits) == 1 and audits[0].previous_status == 'found'


def test_remove_interest_retains_history_and_can_be_restored(client):
    active, engine, _ = client
    active.post('/api/resume', files={'file': ('fixture.docx', resume_docx())})
    result = active.search( json={'mode': 'resume'}).json()
    job_id = result['jobs'][0]['id']
    endpoint = f'/api/jobs/{job_id}/interest'
    selected = active.post(endpoint, json={'turn_id': result['turn_id']}).json()
    assert active.delete(endpoint).json() == {'removed': True}
    assert active.delete(endpoint).status_code == 200
    assert active.get('/api/jobs').json() == []
    assert active.get('/api/bootstrap').json()['counts']['interested'] == 0
    assert active.get('/api/chat').json()[0]['result']['jobs'][0]['status'] == 'dismissed'
    assert active.get(f'/api/jobs/{job_id}').status_code == 404
    assert active.post(f'/api/jobs/{job_id}/mark-applied', json={'explicit_action': True}).status_code == 404
    assert job_id in [j['id'] for j in active.search( json={'mode': 'resume'}).json()['jobs']]
    with Session(engine) as fresh:
        assert fresh.get(JobPosting, job_id)
        assert fresh.exec(select(Application)).one().status == 'dismissed'
        assert len(fresh.exec(select(UserAction).where(UserAction.action == 'remove_interest')).all()) == 1
        assert len(fresh.exec(select(ChatTurn)).all()) == 2
    restored = active.post(endpoint, json={'turn_id': result['turn_id']}).json()
    assert restored['id'] == selected['id'] and restored['status'] == 'interested'
    assert restored['applied_at'] is None
    assert active.get('/api/bootstrap').json()['counts']['interested'] == 1
    assert active.post(f'/api/jobs/{job_id}/mark-applied', json={'explicit_action': True}).status_code == 200
    assert active.delete(endpoint).status_code == 422
    assert active.get(f'/api/jobs/{job_id}').json()['status'] == 'applied'


def test_docx_only_upload_rejects_other_files_and_preserves_current_resume(client):
    active, _, _ = client
    assert active.post('/api/resume', files={'file': ('fixture.DOCX', resume_docx())}).status_code == 200
    stored = active.get('/api/resume').json()
    for filename in ('resume.pdf', 'resume.txt', 'resume.tex', 'resume.doc', 'resume.png', 'resume'):
        response = active.post('/api/resume', files={'file': (filename, b'unsupported file')})
        assert response.status_code == 422
        assert 'Upload a .docx file' in response.json()['detail']
        assert active.get('/api/resume').json() == stored
    response = active.post('/api/resume', files={'file': ('renamed.docx', b'not a Word document')})
    assert response.status_code == 422 and 'valid .docx' in response.json()['detail']
    assert active.get('/api/resume').json() == stored
    assert active.delete('/api/resume').json() == {'removed': True}
    assert active.get('/api/resume').json() is None


def test_bad_model_selection_preserves_stored_resume_with_retry_message(client, monkeypatch):
    from app.resumes import ResumeExtraction, SelectedStatement
    active, _, _ = client
    assert active.post('/api/resume', files={'file': ('fixture.docx', resume_docx())}).status_code == 200
    stored = active.get('/api/resume').json()
    calls = []
    async def invalid(*args, **kwargs):
        calls.append(kwargs)
        return ResumeExtraction(facts=[SelectedStatement(category='experience', statement_id='not-in-source')])
    monkeypatch.setattr('app.resumes.call_tool', invalid)
    response = active.post('/api/resume', files={'file': ('replacement.docx', resume_docx())})
    assert response.status_code == 422
    assert 'upload the .docx file again to retry' in response.json()['detail']
    assert len(calls) == 2
    assert active.get('/api/resume').json() == stored
