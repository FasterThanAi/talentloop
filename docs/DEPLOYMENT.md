# TalentLoop — Deployment (Render + Vercel)

Backend (FastAPI) → **Render**. Frontend (Vite/React) → **Vercel**. Database → **Supabase**.

Do it in this order. Steps 4–6 depend on knowing your live URLs, which you only get after
steps 2 and 3, so there is a deliberate second pass at the end.

Budget ~40 minutes the first time.

---

## The one thing that makes deployment different from localhost

Locally, the SPA and the API are the same site (`localhost`), so cookies "just work".

Deployed, `talentloop.vercel.app` and `talentloop-api.onrender.com` are **different sites**.
A `SameSite=lax` cookie is never sent cross-site, so the refresh token silently disappears
and users get logged out on every reload — with no error anywhere.

This is already handled: setting `APP_ENV=production` switches cookies to
`SameSite=None; Secure` (see `cookie_samesite` in `app/core/config.py`). **If you forget
that one variable, auth will appear to work and then randomly drop sessions.**

---

## 0. Before you start

```bash
cd talentloop
./scripts/verify.sh          # do not deploy something that fails locally
git add -A && git commit -m "chore: deployment config" && git push
```

Render and Vercel both deploy from GitHub, so anything uncommitted does not exist.

---

## 1. Database — Supabase (5 min)

1. supabase.com → your `talentloop` project (or **New project**)
2. **Database → Extensions → enable `vector`** — required before the first migration
3. **Project Settings → Database → Connection string → URI**

   Pick the **Session pooler** connection string, not the direct one:

   ```
   postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```

   **Why the pooler:** Render free instances cold-start and recycle constantly, and each
   one opens its own connection pool. Direct Postgres connections are limited and you will
   hit `too many clients` under almost no load. Use the **Session** pooler (port 5432), not
   the Transaction pooler (6543) — transaction mode does not support the prepared statements
   SQLAlchemy relies on.

4. Replace `[YOUR-PASSWORD]` in the string with your real password. If it contains
   `@ : / ?` or `#`, URL-encode them (`@` → `%40`) or the URI will parse wrongly.

---

## 2. Backend — Render (15 min)

### 2.1 Create the service

Render dashboard → **New → Web Service** → connect your GitHub repo → select `talentloop`.

| Setting | Value |
|---|---|
| Name | `talentloop-api` |
| Language | Python 3 |
| Branch | `main` |
| **Root Directory** | `backend` ← easy to miss, and nothing works without it |
| Build Command | `pip install --upgrade pip && pip install -r requirements.txt` |
| Start Command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |
| Health Check Path | `/api/v1/health` |

> The repo also contains `render.yaml`, so you can instead use **New → Blueprint** and let
> Render read the configuration from the file.

### 2.2 Environment variables

**Environment → Add Environment Variable.** Set these now; the URL-dependent ones come in §4.

```
APP_ENV=production
PYTHON_VERSION=3.12.4
DATABASE_URL=<the Supabase session-pooler URI from step 1>
GEMINI_API_KEY=<your key>
JWT_SECRET=<a long random string — NOT the dev default>
GMAIL_CLIENT_ID=<from Google Cloud Console>
GMAIL_CLIENT_SECRET=<from Google Cloud Console>
GEMINI_MODEL=gemini-2.0-flash
EMBEDDING_MODEL=text-embedding-004
EMBEDDING_DIMENSION=768
HUNTER_ENABLED=false
RIZEOS_ENABLED=false
CREDENTIAL_ANCHOR_ENABLED=false
```

Generate a real secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 2.3 Deploy and verify

Click **Create Web Service**. First build takes 3–5 minutes. When live:

```bash
curl https://talentloop-api.onrender.com/api/v1/health
```

You want:

```json
{"status":"ok","db":true,"pgvector":true,
 "db_dialect":"postgresql","vector_backend":"pgvector","ai_mode":"gemini-2.0-flash"}
```

Check each field — this endpoint exists precisely so you cannot deploy something broken
without noticing:

| Field | Wrong value | Meaning |
|---|---|---|
| `db` | `false` | `DATABASE_URL` wrong, or password not URL-encoded |
| `pgvector` | `false` | you skipped enabling the extension in Supabase |
| `db_dialect` | `sqlite` | `DATABASE_URL` not set — it fell back to the dev default |
| `ai_mode` | `MOCK` | `GEMINI_API_KEY` not set; **every AI result would be fake** |

**Note your backend URL.** Everything below needs it.

---

## 3. Frontend — Vercel (10 min)

Vercel dashboard → **Add New → Project** → import the same repo.

| Setting | Value |
|---|---|
| Framework Preset | Vite |
| **Root Directory** | `frontend` ← click Edit and set this |
| Build Command | `npm run build` (default) |
| Output Directory | `dist` (default) |

**Environment Variables** → add:

```
VITE_API_BASE_URL = https://talentloop-api.onrender.com/api/v1
```

Two things people get wrong here: it must include `/api/v1`, and it must have **no trailing
slash**. Also, Vite bakes `VITE_*` variables in at build time — changing this later requires
a **redeploy**, not just a restart.

Deploy. Note your frontend URL, e.g. `https://talentloop.vercel.app`.

`frontend/vercel.json` is already in the repo with an SPA rewrite. Without it, `/portal`,
`/auth/callback` and `/verify/:hash` return 404 on refresh or direct visit — because those
routes exist only in React Router, not as files on disk.

---

## 4. Second pass — tell each side about the other (5 min)

Now that both URLs exist, go **back to Render → Environment** and add:

```
FRONTEND_URL=https://talentloop.vercel.app
CORS_ORIGINS=https://talentloop.vercel.app
GMAIL_REDIRECT_URI=https://talentloop-api.onrender.com/api/v1/auth/gmail/callback
GOOGLE_REDIRECT_URI=https://talentloop-api.onrender.com/api/v1/auth/google/callback
```

No trailing slashes anywhere. `CORS_ORIGINS` is comma-separated if you need more than one
(a preview deploy, say). Render redeploys automatically on save.

---

## 5. Google Cloud Console — production URIs (5 min)

APIs & Services → **Credentials** → your OAuth client → **Authorised redirect URIs** → add
the two production URLs alongside the existing localhost ones:

```
http://127.0.0.1:8000/api/v1/auth/gmail/callback     ← keep
http://127.0.0.1:8000/api/v1/auth/google/callback    ← keep
https://talentloop-api.onrender.com/api/v1/auth/gmail/callback
https://talentloop-api.onrender.com/api/v1/auth/google/callback
```

**Save.** Forgetting this gives the same `redirect_uri_mismatch` you already hit — the URI
must match byte for byte, and `https://…onrender.com/…` is a completely different string
from `http://127.0.0.1:8000/…`.

While you are there: OAuth consent screen → confirm your demo Google accounts are under
**Test users**, since the app is unverified.

---

## 6. Seed the demo data

Render's free plan has no shell, so run the seed from your machine against the production
database:

```bash
cd backend
source .venv/bin/activate
DATABASE_URL='<the same Supabase session-pooler URI>' python -m app.seed --reset --demo
```

`--reset` truncates first, so this is safe to re-run between rehearsals.

---

## 7. Verify the deployed system

Open your Vercel URL and walk the path:

- [ ] No red banner at the top of the app (a banner means mock AI or SQLite — see §2.3)
- [ ] Register a recruiter → land on Requisitions
- [ ] Reload the page → **still logged in** (this is the cross-site cookie test)
- [ ] Sign in with Google → completes and lands correctly
- [ ] Open a requisition → click a score → evidence drawer opens with citations
- [ ] Approve and send one outreach email → it arrives
- [ ] Try sending an unapproved draft → 409
- [ ] Release one feedback report → read it in the candidate portal
- [ ] Visit `/portal` directly and hard-refresh → loads, does not 404

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Render: "no open ports detected" | Hard-coded port | Start command must use `--port $PORT` |
| Render build succeeds, start crashes | Migration failed | Check logs; usually `DATABASE_URL` or missing `vector` extension |
| Browser console: CORS error | Origin not allowed | `CORS_ORIGINS` must exactly match the Vercel origin, no trailing slash |
| Logged out on every refresh | `APP_ENV` not `production` | Cookie stayed `SameSite=lax`; cross-site never sends it |
| `redirect_uri_mismatch` | Production URIs not registered | §5 |
| 404 on `/portal` after refresh | Missing SPA rewrite | `frontend/vercel.json` — confirm Root Directory is `frontend` |
| API calls hit `127.0.0.1` in production | Stale build | `VITE_API_BASE_URL` is baked in at build time; redeploy |
| `too many clients already` | Direct Postgres connection | Use the Supabase **session pooler** URI |
| First request takes ~50s | Free-tier cold start | Hit the URL 2 minutes before demoing, or use an uptime pinger |
| AI responses look canned | `ai_mode: MOCK` | `GEMINI_API_KEY` missing on Render |

---

## Demo-day notes

**Free Render instances sleep after 15 minutes of inactivity** and take roughly 50 seconds to
wake. Open the app a few minutes before you present, or set a free uptime monitor
(uptimerobot.com) pinging `/api/v1/health` every 10 minutes the day of the demo.

Deploy at least 24 hours before you present. Every problem in the table above is
ten minutes to fix with time in hand, and fatal with an audience waiting.
