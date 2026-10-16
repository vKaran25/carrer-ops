"""Supabase token verification and server-managed invitation eligibility."""
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.config import get_settings
from app.models import AuthIdentity, Invitation, User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    subject: str | None
    email: str | None


@lru_cache(maxsize=4)
def jwks(url: str):
    return jwt.PyJWKClient(url.rstrip('/') + '/auth/v1/.well-known/jwks.json',
                           cache_jwk_set=True, lifespan=60, timeout=10)


def authenticate(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    settings = get_settings()
    if settings.auth_mode == 'local':
        if settings.environment != 'development':
            raise HTTPException(503, 'Authentication is not configured.')
        return Principal(None, None)
    if not credentials or credentials.scheme.casefold() != 'bearer':
        raise HTTPException(401, 'Sign in to access your workspace.', headers={'WWW-Authenticate': 'Bearer'})
    token = credentials.credentials
    if len(token) > 16384:
        raise HTTPException(401, 'Invalid session.')
    try:
        key = jwks(settings.supabase_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(token, key.key, algorithms=['ES256', 'RS256'],
                            audience='authenticated', issuer=settings.supabase_url.rstrip('/') + '/auth/v1',
                            options={'require': ['exp', 'iat', 'sub', 'iss', 'aud']})
        subject = str(UUID(claims['sub']))
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, 'Your session is invalid or expired. Sign in again.') from None
    # Confirm verified email with Auth, never user-editable metadata in the JWT.
    try:
        response = httpx.get(settings.supabase_url.rstrip('/') + '/auth/v1/user',
                             headers={'apikey': settings.supabase_publishable_key,
                                      'Authorization': 'Bearer ' + token}, timeout=10)
        if response.status_code in (401, 403):
            raise HTTPException(401, 'Your session is no longer valid. Sign in again.')
        response.raise_for_status()
        user = response.json()
        if user.get('id') != subject or not user.get('email_confirmed_at') or not user.get('email'):
            raise HTTPException(403, 'A verified email is required for this beta.')
        return Principal(subject, user['email'].strip().casefold())
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise HTTPException(503, 'The authentication service is unavailable. Try again shortly.') from None


def bind_workspace(session: Session, principal: Principal):
    if principal.subject is None:
        session.info['user_id'] = 1
        return
    # Every request checks the allowlist; revocation does not wait for JWT expiry.
    invitation = session.exec(select(Invitation).where(Invitation.email == principal.email,
                              Invitation.enabled == True).with_for_update()).first()
    if not invitation:
        raise HTTPException(403, 'This beta is invitation-only. Contact the operator for access.')
    identity = session.get(AuthIdentity, principal.subject)
    if identity is None:
        user = User(email=principal.email, auth_provider='supabase')
        session.add(user)
        session.flush()
        identity = AuthIdentity(subject=principal.subject, user_id=user.id)
        session.add(identity)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            identity = session.get(AuthIdentity, principal.subject)
            if identity is None:
                raise HTTPException(409, 'Account setup changed. Sign in again.') from None
    session.info['user_id'] = identity.user_id
    session.info['auth_subject'] = principal.subject
    session.info['email'] = principal.email
    user = session.get(User, identity.user_id)
    user.email = principal.email
    session.add(user)
    session.commit()  # release invitation lock before any model or source calls


def recheck_access(session: Session):
    if get_settings().auth_mode == 'local':
        return
    invitation = session.exec(select(Invitation).where(Invitation.email == session.info.get('email'),
                              Invitation.enabled == True).with_for_update()
                              .execution_options(populate_existing=True)).first()
    identity = session.get(AuthIdentity, session.info.get('auth_subject'))
    if not invitation or not identity or identity.user_id != session.info.get('user_id'):
        raise HTTPException(403, 'Access was revoked or the account was deleted.')
