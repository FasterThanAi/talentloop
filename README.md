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
