# TalentLoop — Project Context

## What this product is
TalentLoop is an agentic hiring assistant. A recruiter gives it a job description; it sources
candidates from permitted sources, researches each against public evidence, scores fit against a
fixed rubric with citations, drafts personalised outreach, triages replies, and issues an
explainable feedback report to every candidate it evaluates — shortlisted or not.

Users: (1) recruiters/founders at small companies, (2) campus placement officers,
(3) candidates, who are first-class users with their own portal, not database rows.

## Two invariants — never violate these
1. THE MODEL NEVER PRODUCES THE FINAL SCORE.
   Gemini rates individual rubric dimensions against cited evidence and returns structured JSON.
   Deterministic Python in `app/rubric/` computes the weighted 0–100 score. If you are about to
   write a prompt that asks for an overall score, or read a `score` field straight off a model
   response, you are doing it wrong.
2. NOTHING REACHES A HUMAN WITHOUT EXPLICIT APPROVAL.
   No email send, no feedback release, no candidate-visible artefact happens as a side effect of
   another action. Approval is a separate API call that records who approved and when. Enforce it
   in middleware (`app/core/guards.py`), never only in the UI.

## Non-negotiable rules
- Never scrape gated platforms (LinkedIn et al.), bypass logins/CAPTCHAs, or ignore robots.txt.
- Never persist raw scraped HTML. Store extracted structured findings plus the source URL only.
- Never pass name, photo, age, gender, or institution prestige into the scoring prompt.
  Scoring inputs are skills, evidence and role requirements only.
- `do_not_contact` is checked by middleware before ANY outbound action, and is irreversible.
- There is no automated rejection path anywhere in the product. Low scores rank lower; humans decide.
- Never edit files in `app/ai/prompts/` as a side effect of another task. Prompt changes are
  deliberate, reviewed, and require a version bump (v1 → v2), because stored scores reference
  `rubric_version` and must stay interpretable.

## Architecture
- Monolith with module boundaries. FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL/pgvector.
- Routers are thin: validate, authorise, delegate to a service, return. No business logic in `api/`.
- Services own their tables and never import each other's internals; cross-service calls go
  through the public function surface of the other service.
- All AI calls go through `app/ai/client.py`. Never call the Gemini SDK directly from a service.
- Long-running work returns a `job_id` immediately and is polled. No request may block on a
  model call. Jobs commit progress per item so a crash never loses a whole batch.
- Multi-tenant: every business table carries `org_id`; the base repository applies the filter.
  Never write a raw query that omits it.

## Code conventions
- Python 3.11/3.12, full type hints, `ruff` clean. Functions do one thing; extract rather than nest.
- Pydantic v2 models for every LLM response. A model reply that fails validation is retried ONCE
  with the violation quoted back, then the item is marked `needs_review`. Never coerce, never
  silently default, never `try/except: pass`.
- Errors use one problem-detail envelope: `{type, title, status, detail, code}`.
- Every AI call logs: model, prompt file + version, input token count, output token count,
  latency, and the entity it was called for.
- Alembic migration for every schema change. Never edit a migration that has been applied.
- Tests live beside the behaviour they test. Evaluation sets live in `backend/tests/eval/`.

## Frontend conventions
- React 18 + Vite + Tailwind + TanStack Query. See `docs/prompts/ui-system.md` before any UI work.
- Server state belongs to TanStack Query. Never mirror it into `useState`.
- Every list view handles four states explicitly: loading, empty, error, populated.
- A score is NEVER rendered without its reasoning reachable in one click.

## What "done" means
A change is done when: it compiles, `ruff` and type checks pass, the phase's acceptance checks in
the build playbook pass, and no invariant above was weakened to make it work.

## When you are unsure
Ask rather than guess, and prefer the boring option. If a requirement seems to conflict with an
invariant, the invariant wins and the requirement is wrong.
