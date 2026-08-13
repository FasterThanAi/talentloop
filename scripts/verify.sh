#!/usr/bin/env bash
# TalentLoop — one-command readiness check.
#
#   ./scripts/verify.sh
#
# Runs everything that can be checked without a human, prints a pass/fail table, and exits
# non-zero if anything demo-critical is broken. Run this before every rehearsal.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
PASS=0; FAIL=0; WARN=0
RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'

ok()   { printf "  ${GRN}PASS${RST}  %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  ${RED}FAIL${RST}  %s\n" "$1"; FAIL=$((FAIL+1)); }
warn() { printf "  ${YEL}WARN${RST}  %s\n" "$1"; WARN=$((WARN+1)); }
head() { printf "\n${DIM}── %s ${RST}\n" "$1"; }

printf "\nTalentLoop readiness check\n"

# ─────────────────────────────────────────────────────────── repo hygiene
head "Repository hygiene"
git ls-files | grep -qE "(^|/)\.env$" && bad ".env is tracked by git — remove it and rotate keys" || ok ".env is not tracked"
grep -q "^\.env" .gitignore && ok ".gitignore excludes .env" || bad ".gitignore does not exclude .env"
[ -f CLAUDE.md ] && ok "CLAUDE.md present" || bad "CLAUDE.md missing"
[ -f .github/workflows/ci.yml ] && ok "CI workflow present" || bad "CI workflow missing"
if git status --porcelain | grep -q .; then
  warn "uncommitted changes: $(git status --porcelain | wc -l | tr -d ' ') file(s)"
else
  ok "working tree clean"
fi

# ─────────────────────────────────────────────────────────── invariants
head "Invariants (the two things that must never break)"
if grep -qi "Do NOT produce an overall score" backend/app/ai/prompts/score.v1.md; then
  ok "Invariant 1: scoring prompt forbids an overall score"
else
  bad "Invariant 1 BROKEN: score.v1.md no longer forbids an overall score"
fi
grep -q "def compute_fit_score" backend/app/rubric/compute.py \
  && ! grep -q "genai" backend/app/rubric/compute.py \
  && ok "Invariant 1: aggregation is pure Python" \
  || bad "Invariant 1 BROKEN: compute.py missing or calls a model"
grep -q "require_approved" backend/app/services/outreach.py && ok "Invariant 2: outreach send requires approval" || bad "Invariant 2 BROKEN: outreach send has no approval guard"
grep -q "require_response_approved" backend/app/services/conversation.py && ok "Invariant 2: reply send requires approval" || bad "Invariant 2 BROKEN: reply send has no approval guard"
grep -q "assert_contactable" backend/app/services/feedback.py && ok "Invariant 2: feedback release checks do-not-contact" || bad "Invariant 2 BROKEN: feedback release skips do-not-contact"
if grep -rqE "send_immediately|auto_send|skip_approval" backend/app 2>/dev/null; then
  bad "an approval-bypass flag exists in backend/app"
else
  ok "no approval-bypass flags"
fi

# ─────────────────────────────────────────────────────────── backend
head "Backend"
cd backend || exit 1
if [ -d .venv ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null
  ok "virtualenv activated"
else
  warn "no backend/.venv — using system python"
fi

python -c "import fastapi" 2>/dev/null && ok "dependencies importable" || { bad "dependencies missing — run: pip install -r requirements.txt"; }

python - <<'PY' 2>/dev/null && ok "all modules import cleanly" || bad "import error — see: python -c 'import app.main'"
import app.main  # noqa
PY

if command -v ruff >/dev/null 2>&1; then
  ruff check . >/tmp/ruff.log 2>&1 && ok "ruff clean" || { bad "ruff issues — see /tmp/ruff.log"; tail -5 /tmp/ruff.log; }
else
  warn "ruff not installed"
fi

alembic upgrade head >/tmp/alembic.log 2>&1 && ok "migrations apply to head" || { bad "migration failure — see /tmp/alembic.log"; tail -5 /tmp/alembic.log; }

pytest tests/unit -q >/tmp/unit.log 2>&1 && ok "unit tests pass" || { bad "unit test failures — see /tmp/unit.log"; tail -8 /tmp/unit.log; }

# ─────────────────────────────────────────────────────────── evals
head "Evaluation gates"
pytest tests/eval/bias_probes.py -q >/tmp/bias.log 2>&1 && ok "bias probes within tolerance" || { bad "BIAS PROBE FAILURE — see /tmp/bias.log"; tail -8 /tmp/bias.log; }
pytest tests/eval/feedback_fidelity.py -q >/tmp/fid.log 2>&1 && ok "feedback fidelity: no unsupported claims" || { bad "feedback fidelity failure — see /tmp/fid.log"; tail -8 /tmp/fid.log; }
pytest tests/eval/scoring_eval.py -q >/tmp/score.log 2>&1 && ok "scoring evaluation runs" || { warn "scoring eval issue — see /tmp/score.log"; }

# ─────────────────────────────────────────────────────────── runtime config
head "Runtime configuration"
python - <<'PY'
import sys
sys.path.insert(0, ".")
try:
    from app.core.config import settings
    from app.core.vector import vector_backend
    from app.ai.client import ai_is_mocked
except Exception as e:
    print(f"  \033[31mFAIL\033[0m  cannot load config: {e}")
    sys.exit(0)

pg = settings.DATABASE_URL.startswith(("postgresql", "postgres://"))
print(f"  \033[32mPASS\033[0m  database: postgresql" if pg
      else "  \033[33mWARN\033[0m  database: SQLITE — switch DATABASE_URL to Supabase before the demo")
vb = vector_backend()
print(f"  \033[32mPASS\033[0m  vector backend: {vb}" if vb == "pgvector"
      else f"  \033[33mWARN\033[0m  vector backend: {vb} (pgvector inactive)")
if ai_is_mocked():
    print("  \033[31mFAIL\033[0m  AI MOCK MODE — every model result is canned. Set GEMINI_API_KEY.")
else:
    print(f"  \033[32mPASS\033[0m  AI live: {settings.GEMINI_MODEL}")
print("  \033[32mPASS\033[0m  Gmail configured" if settings.GMAIL_CLIENT_ID
      else "  \033[33mWARN\033[0m  Gmail not configured — sending will not work")
PY

# ─────────────────────────────────────────────────────────── frontend
head "Frontend"
cd "$ROOT/frontend" || exit 1
[ -d node_modules ] && ok "node_modules installed" || warn "run npm install"
if [ -d node_modules ]; then
  npm run build >/tmp/fe.log 2>&1 && ok "frontend builds" || { bad "frontend build failed — see /tmp/fe.log"; tail -8 /tmp/fe.log; }
fi

# ─────────────────────────────────────────────────────────── manual
head "Requires a human (not checked here)"
cat <<'MANUAL'
  [ ] Boot both apps; /health shows db_dialect=postgresql, vector_backend=pgvector, ai_mode!=MOCK
  [ ] python -m app.seed --reset --demo  →  40 scored candidates with a realistic spread
  [ ] Click a score → evidence drawer opens with dimensions, citations, confidence
  [ ] Approve + send one outreach email → it arrives in a real inbox
  [ ] Try sending an unapproved draft → 409
  [ ] Mark a candidate do-not-contact → send AND feedback release both blocked
  [ ] Release one feedback report → read it in the candidate portal
  [ ] Audit trail shows parse, score, draft, approve, send, release with the right actor
  [ ] Backup demo video recorded
MANUAL

printf "\n${DIM}────────────────────────────────────────${RST}\n"
printf "  ${GRN}%d passed${RST}   ${RED}%d failed${RST}   ${YEL}%d warnings${RST}\n\n" "$PASS" "$FAIL" "$WARN"
[ "$FAIL" -eq 0 ] || exit 1
