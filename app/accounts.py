"""Immediate active-workspace deletion, followed by retryable Auth cleanup."""
from pathlib import Path
import re
import shutil

import httpx
from fastapi import HTTPException
from sqlalchemy import delete
from sqlmodel import Session, select

from app.config import get_settings
from app.models import (Application, AuthIdentity, ChatTurn, DailyUsage, DeletionRequest,
                        Invitation, JobPosting, MemoryFact, PersonalizationConsent, ResumeProfile,
                        ScoringWeights, SearchContext, SearchPreferences, SearchRun, User, UserAction)
from app.workspace import user_id


async def delete_account(session: Session):
    if get_settings().auth_mode != 'supabase':
        raise HTTPException(409, 'Account deletion is available for authenticated accounts.')
    actor, subject = user_id(session), session.info['auth_subject']
    from app.auth import recheck_access
    recheck_access(session)
    session.exec(select(User).where(User.id == actor).with_for_update()).one()
    applications = session.exec(select(Application).join(JobPosting).where(JobPosting.user_id == actor)).all()
    artifact_ids = [a.curated_resume.get('artifact_id') for a in applications if a.curated_resume]
    ids = [a.id for a in applications]
    session.exec(delete(UserAction).where(UserAction.user_id == actor))
    if ids:
        session.exec(delete(Application).where(Application.id.in_(ids)))
    for model in (SearchRun, ChatTurn, SearchContext, SearchPreferences, MemoryFact, ScoringWeights,
                  PersonalizationConsent, ResumeProfile, AuthIdentity, JobPosting):
        session.exec(delete(model).where(model.user_id == actor))
    session.exec(delete(DailyUsage).where(DailyUsage.scope == f'user:{actor}'))
    invitation = session.get(Invitation, session.info['email'])
    if invitation:
        invitation.enabled = False
        session.add(invitation)
    session.exec(delete(User).where(User.id == actor))
    session.add(DeletionRequest(subject=subject, artifact_ids=[i for i in artifact_ids if isinstance(i, str)]))
    session.commit()
    cleaned = clean_artifacts(artifact_ids)
    auth_deleted = cleaned and await delete_auth_identity(subject)
    if auth_deleted:
        session.exec(delete(DeletionRequest).where(DeletionRequest.subject == subject))
        session.commit()
    return {'deleted': True, 'auth_cleanup': 'complete' if auth_deleted else 'pending', 'artifact_cleanup': 'complete' if cleaned else 'pending',
            'notice': 'Your active database workspace was deleted and its invitation revoked. Remaining owned-file/Auth cleanup is queued; no application backup is retained.'}


def clean_artifacts(artifact_ids):
    base = Path(get_settings().artifact_dir).resolve()
    for artifact_id in artifact_ids:
        if isinstance(artifact_id, str) and re.fullmatch('[a-f0-9]{32}', artifact_id):
            path = (base / artifact_id).resolve()
            if path.parent == base and path.is_dir():
                try:
                    shutil.rmtree(path)
                except OSError:
                    return False
    return True


async def delete_auth_identity(subject: str) -> bool:
    settings = get_settings()
    if not settings.supabase_secret_key:
        return False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(settings.supabase_url.rstrip('/') + '/auth/v1/admin/users/' + subject,
                headers={'apikey': settings.supabase_secret_key, 'Authorization': 'Bearer ' + settings.supabase_secret_key}, timeout=15)
            if response.status_code != 404:
                response.raise_for_status()
            return True
    except httpx.HTTPError:
        return False


async def process_deletions(engine):
    with Session(engine) as session:
        rows = session.exec(select(DeletionRequest).limit(5)).all()
        pending = [(row.subject, row.artifact_ids) for row in rows]
    for subject, artifact_ids in pending:
        if clean_artifacts(artifact_ids) and await delete_auth_identity(subject):
            with Session(engine) as session:
                session.exec(delete(DeletionRequest).where(DeletionRequest.subject == subject))
                session.commit()
