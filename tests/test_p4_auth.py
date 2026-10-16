"""Signed JWT verification using generated keys and fictional Auth responses."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import httpx
import jwt
import pytest

from app import auth
from app.config import get_settings


@pytest.fixture
def signed(monkeypatch):
    settings=get_settings()
    monkeypatch.setattr(settings,'auth_mode','supabase')
    monkeypatch.setattr(settings,'supabase_url','https://fictional.supabase.co')
    monkeypatch.setattr(settings,'supabase_publishable_key','sb_publishable_fixture')
    key=ec.generate_private_key(ec.SECP256R1())
    monkeypatch.setattr(auth,'jwks',lambda _:SimpleNamespace(get_signing_key_from_jwt=lambda _:SimpleNamespace(key=key.public_key())))
    now=datetime.now(timezone.utc)
    claims={'sub':str(uuid4()),'iss':'https://fictional.supabase.co/auth/v1','aud':'authenticated','iat':now,'exp':now+timedelta(minutes=5)}
    user={'id':claims['sub'],'email':'fixture@example.invalid','email_confirmed_at':now.isoformat()}
    calls=[]
    def verified(url,**kwargs):
        calls.append(url)
        return httpx.Response(200,json=user,request=httpx.Request('GET',url))
    monkeypatch.setattr(auth.httpx,'get',verified)
    def credentials(patch=None):
        token=jwt.encode({**claims,**(patch or {})},key,algorithm='ES256')
        return HTTPAuthorizationCredentials(scheme='Bearer',credentials=token)
    return credentials,user,calls


def test_signed_token_verified_email_and_fixed_project_endpoint(signed):
    credentials,user,calls=signed
    principal=auth.authenticate(credentials())
    assert principal.subject==user['id'] and principal.email==user['email']
    assert calls==['https://fictional.supabase.co/auth/v1/user']


@pytest.mark.parametrize('patch',[
    {'iss':'https://attacker.invalid/auth/v1'}, {'aud':'anonymous'},
    {'exp':datetime.now(timezone.utc)-timedelta(seconds=10)}, {'sub':'not-a-uuid'},
])
def test_invalid_signed_claims_are_rejected_before_user_lookup(signed,patch):
    credentials,_,calls=signed
    with pytest.raises(HTTPException) as exc:auth.authenticate(credentials(patch))
    assert exc.value.status_code==401 and not calls


def test_missing_token_is_unauthorized(signed):
    with pytest.raises(HTTPException) as exc:auth.authenticate(None)
    assert exc.value.status_code==401


def test_unverified_auth_email_is_forbidden(signed):
    credentials,user,_=signed
    user['email_confirmed_at']=None
    with pytest.raises(HTTPException) as exc:auth.authenticate(credentials())
    assert exc.value.status_code==403


def test_auth_service_failure_is_reported(signed,monkeypatch):
    credentials,_,_=signed
    def unavailable(*args,**kwargs):raise httpx.ConnectError('fixture outage')
    monkeypatch.setattr(auth.httpx,'get',unavailable)
    with pytest.raises(HTTPException) as exc:auth.authenticate(credentials())
    assert exc.value.status_code==503
