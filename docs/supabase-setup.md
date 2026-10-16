# Supabase setup — P4 implementation

Updated 16 October 2026. The adapter, login routes and initial schema are written but not yet accepted. No tests or personal-resume processing were run during this implementation pass. The user chose an empty PostgreSQL workspace, with no SQLite data import. Adding staged settings alone does not activate PostgreSQL.

## 1. Root environment settings

Copy the **Session pooler** URI from Supabase Dashboard → Connect. Put the real password into the URI locally, percent-encoding reserved password characters. Keep all credentials out of chat and Git.

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
SUPABASE_DATABASE_URL=YOUR_SESSION_POOLER_URI
SUPABASE_SECRET_KEY=YOUR_BACKEND_ONLY_SECRET_KEY
```

The publishable key is browser-safe; a secret/service-role key must never be placed in that field. The elevated secret is used only by FastAPI for Supabase Auth account deletion. Active workspace deletion revokes the invitation immediately; remote deletion failures remain queued for cleanup.

For verified production database TLS, download the project's CA certificate from Supabase Database Settings → SSL Configuration and save it at `data/supabase/prod-ca-2021.crt` (or set `DATABASE_SSL_ROOT_CERT` to its local path). The adapter uses `verify-full` when the file is present and requires it in production. Development setup without this file uses encrypted `require` mode, which does not verify server identity. [Supabase SSL guidance](https://supabase.com/docs/guides/platform/ssl-enforcement).

Session pooling was selected for the persistent FastAPI service. See [connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres) and [API key types](https://supabase.com/docs/guides/getting-started/api-keys).

## 2. Explicit activation after settings are ready

The agent is waiting for the user's key-ready notification before activating the staged connection. When ready, the implementation command is:

```powershell
.venv/Scripts/python.exe scripts/configure_supabase.py --activate
```

This runs Alembic against a private `career_ops` schema, then selects `DATABASE_URL` and `AUTH_MODE=supabase` in root `.env`. It never reads or imports SQLite records. PostgreSQL startup checks the migration revision instead of calling runtime `create_all`. Do not edit an applied baseline migration; subsequent schema changes need a new revision.

Restart FastAPI after activation. The same SvelteKit frontend retrieves only public Auth configuration from the backend; no duplicate frontend secret environment is needed. Use one frontend origin consistently, such as `http://127.0.0.1:5173`.

The normal application database is PostgreSQL in this mode. The offline GeoNames city index remains a separate public-data SQLite file; it contains no account records.

## 3. Allowlist invitations

The user will manage the addresses. These commands grant/revoke access and send no messages:

```powershell
.venv/Scripts/python.exe scripts/operator.py invite first@example.com second@example.com
.venv/Scripts/python.exe scripts/operator.py list
.venv/Scripts/python.exe scripts/operator.py revoke first@example.com
```

Use the exact verified email used for Google or email-link login. Every private API request independently checks the invitation, and revocation cancels unfinished searches. Verified Supabase UUIDs map to internal account IDs. An uninvited Auth identity does not receive an application workspace.

The schema is private, with RLS enabled and browser roles denied access. Browser requests use authenticated FastAPI routes; the publishable key does not grant access to application tables.

## 4. Google and PKCE redirects

In Supabase Authentication → URL Configuration:

- Site URL: `http://127.0.0.1:5173`
- Additional redirect: `http://127.0.0.1:5173/auth/callback`

Create a Google Cloud OAuth web client and configure its ID/secret in Supabase's Google provider. Google's redirect URI is the Supabase callback shown in that provider panel, not the application callback. Keep the client secret in provider settings. Configure the Google consent audience/test users as required by your Google project. Follow [Supabase's Google guide](https://supabase.com/docs/guides/auth/social-login/auth-google).

Use an asymmetric Supabase JWT signing key (ES256/RS256), available through the project's JWKS endpoint. FastAPI validates issuer, audience, signature and expiry, then confirms verified email with Supabase Auth; it does not trust user-editable JWT metadata. The selected SDK cookies remain browser-readable, as required by the standard PKCE integration. [Signing keys](https://supabase.com/docs/guides/auth/signing-keys).

Production HTTPS origins and hosting remain a P5A decision after capacity testing.

## 5. Passwordless email and Resend

Both login flows are implemented. The user approved configuring SMTP later and using Google meanwhile. Supabase's default sender is restricted to organization-team addresses, so it is not delivery readiness for ordinary testers. [Supabase SMTP requirements](https://supabase.com/docs/guides/auth/auth-smtp).

For Resend, first obtain a domain you control, add it in Resend, and publish the DNS records Resend supplies until verification passes. Domain purchase and DNS changes are user setup; no purchase was made here.

In Supabase custom SMTP settings, use:

- Host: `smtp.resend.com`
- Port: `465` for implicit TLS, or `587` for STARTTLS
- Username: `resend`
- Password: your Resend API key
- Sender: an address on your verified domain

Store these credentials in Supabase's SMTP settings, not frontend code. Follow [Resend SMTP setup](https://resend.com/docs/send-with-smtp). Actual delivery, redirect and expiry acceptance will be checked only when the user authorizes testing.

## 6. Acceptance still pending

Schema activation, real PostgreSQL isolation/audit/concurrency, Google/email login, logout/refresh, account deletion, queue recovery and live discovery quality remain unverified. The previous 189/27 prototype test counts do not validate these source changes. The user will place DOCX resumes in an ignored folder and explicitly authorize a later test pass.
