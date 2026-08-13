# TalentLoop — Agentic Hiring Assistant

> **Ethical AI & Responsible Innovation** — RizeOS Hackathon 2026

TalentLoop is an agentic hiring assistant that parses job descriptions, sources candidates from consent-safe channels, researches evidence on public pages, computes explainable fit scores against a transparent rubric, drafts personalized outreach, triages inbound replies, and issues role-relative feedback reports to candidates.

## Two Non-Negotiable Invariants
1. **The Model Never Produces the Final Score.**
   Gemini rates individual rubric dimensions against cited evidence; deterministic Python in `app/rubric/compute.py` performs the weighted aggregation and applies confidence caps.
2. **Nothing Reaches a Human Without Explicit Approval.**
   No email dispatch, no feedback report release, and no candidate-visible artifact is sent automatically. Every outbound action is approval-gated and audited.

*Note on prior work: Proven core modules (Gmail OAuth, text extraction, knowledge chunking) have been ported deliberately from our prior work, adapted cleanly to the recruiting domain.*

---

## Quickstart (Under 10 Commands)

### 1. Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.seed --demo
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Visit:
- Recruiter Dashboard: `http://localhost:5173` (Demo login: `demo@talentloop.dev` / `password123`)
- Candidate Portal: `http://localhost:5173/portal` (Candidate login: `candidate1@example.com` / `password123`)
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`

---

## Before Every Demo — run the checks

```bash
./scripts/verify.sh          # migrations, tests, evals, config sanity — exits non-zero on failure
python3 scripts/audit_phases.py   # every phase acceptance criterion, statically
```

`verify.sh` proves the software runs. `audit_phases.py` proves nothing specified went missing.
CI runs both on every pull request, and the evaluation job is a **gate** — a scoring-prompt or
rubric change that pushes a matched-pair bias probe beyond tolerance fails the build.

### Two settings that must be right before you demo

`GET /api/v1/health` reports both, and the UI shows a banner when either is wrong:

| Field | Demo value | If wrong |
|---|---|---|
| `ai_mode` | your Gemini model | `MOCK` means every AI result on screen is **canned**. Set `GEMINI_API_KEY`. |
| `db_dialect` / `vector_backend` | `postgresql` / `pgvector` | SQLite is a local-dev fallback: no pgvector search, and append-only audit cannot be enforced. Point `DATABASE_URL` at Supabase. |

The system is deliberately loud about both. A demo that silently runs on mock AI or SQLite would
misrepresent what was built, so it is designed to be impossible to do by accident.

---

## Where things live

| Path | What |
|---|---|
| `backend/app/rubric/` | The scoring rubric and the **pure-Python** weighted aggregation (Invariant 1) |
| `backend/app/core/guards.py` | Approval and do-not-contact guards (Invariant 2) |
| `backend/app/ai/prompts/` | Versioned production prompts — change these deliberately, with a version bump |
| `backend/app/core/vector.py` | Dialect-aware embedding column: real `vector(N)` on Postgres, JSON on SQLite |
| `backend/tests/eval/` | Bias probes, scoring evaluation, feedback fidelity — the CI gate |
| `CLAUDE.md` | Global context loaded by the coding agent in every session |
| `docs/prompts/` | UI system prompt and API contract |
| `docs/GIT-WORKFLOW.md` | Team branching, review and merge process |
