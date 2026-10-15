# Supabase setup — user steps

The user selected the standard Supabase SvelteKit PKCE/cookie integration on 15 October 2026. The SDK manages cookie storage/refresh; FastAPI must independently validate access tokens and invite eligibility. These are selected implementation requirements, **not currently implemented login/database features**. The local app still uses SQLite/user 1.

## 1. Create the project

1. Open the [Supabase dashboard](https://supabase.com/dashboard), sign in and choose **New project** in a free organization.
2. Name it `career-ops` (or your preferred name). Select a region appropriate for the intended hosting/users; record it for the hosting discussion.
3. Generate a strong database password and save it in your password manager. Create the project and wait until it is ready. Keep this beta project empty; do not import your local resume/history/database.

## 2. Save the project URL and publishable key locally

Open the project's **Connect** dialog or **Settings → API Keys**. Copy the project URL and **publishable key**. Add these to the repository-root `.env`:

```dotenv
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
```

These names are reserved for the forthcoming adapter; the current app does not use them. Leave the existing `DATABASE_URL=sqlite:///./data/career_ops.db` unchanged. Do not copy a secret/service-role key into frontend settings or commit `.env`. Keep the database password/connection strings local; do not paste credentials into chat.

The publishable key is intended for public application use; it does not replace authenticated authorization or database ownership controls. See [API keys](https://supabase.com/docs/guides/getting-started/api-keys). Database connection mode and migration settings will be chosen explicitly with the adapter/hosting work; [connection choices](https://supabase.com/docs/guides/database/connecting-to-postgres).

## 3. Prepare local auth redirects

In **Authentication → URL Configuration**, use the same local host throughout:

- Site URL: `http://127.0.0.1:5173`
- Additional redirect URL for the planned callback: `http://127.0.0.1:5173/auth/callback`

The callback is planned, not available in the current app. Production HTTPS URLs will be added once hosting is chosen. Avoid mixing `localhost` with `127.0.0.1` during the PKCE flow. [Redirect configuration](https://supabase.com/docs/guides/auth/redirect-urls).

## 4. Provider setup comes with the login implementation

Google login needs a Google Cloud OAuth web client and its credentials entered in Supabase's Google provider configuration. Google's authorized redirect URI is the **Supabase callback URL shown in the dashboard**, not the application's `/auth/callback`. Follow the [official Google setup](https://supabase.com/docs/guides/auth/social-login/auth-google); keep the client secret in provider settings.

Email links to ordinary beta testers require custom SMTP; Supabase's default sender is restricted to team addresses. SMTP provider/domain selection remains a user decision before implementation. Do not treat the default sender as beta email readiness. [SMTP requirements](https://supabase.com/docs/guides/auth/auth-smtp).

Once steps 1–2 are ready, tell the agent **“Supabase project created; settings added locally.”** No keys/passwords are needed in chat. Real login/PostgreSQL tests remain pending until the adapter, providers, invitations and migrations are implemented; existing local data must remain untouched.

## Selected session design

Use the standard SvelteKit integration with PKCE and shared SDK cookies; those cookies are browser-readable. Do not introduce a custom HttpOnly session store without another decision. Verify tokens server-side; do not trust decoded/unverified session data, client-supplied user IDs or a publishable key alone. Do not cache authenticated responses across users. Full privacy, ownership, invitation, revocation and production acceptance remain required. [Supabase framework/session guidance](https://supabase.com/docs/guides/auth/server-side/advanced-guide).
