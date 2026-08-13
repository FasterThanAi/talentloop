#!/usr/bin/env python3
"""
Phase acceptance audit.

Checks the Round 2 playbook's acceptance criteria against the repository, statically.
It answers "does the specified thing exist and look right", NOT "does the software run" —
for that, use scripts/verify.sh, which actually executes migrations, tests and evals.

    python3 scripts/audit_phases.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
checks: dict[str, list[tuple[str, int]]] = defaultdict(list)


def rd(rel: str) -> str:
    fp = os.path.join(ROOT, rel)
    if not os.path.isfile(fp):
        return ""
    return open(fp, encoding="utf-8", errors="ignore").read()


def ex(rel: str) -> bool:
    return os.path.exists(os.path.join(ROOT, rel))


def sh(cmd: str) -> str:
    try:
        return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True).stdout
    except Exception:
        return ""


def add(ph: str, label: str, cond: bool) -> None:
    checks[ph].append((label, 1 if cond else 0))


def unk(ph: str, label: str) -> None:
    checks[ph].append((label, -1))


def body_after(src: str, marker: str) -> str:
    return src.split(marker)[-1] if marker in src else ""


def strip_docstrings(src: str) -> str:
    return re.sub(r'"""(?:.|\n)*?"""', "", src)


# ─────────────────────────────────────────────────────────────── load sources
main = rd("backend/app/main.py")
models = rd("backend/app/models/__init__.py")
cl = rd("backend/app/ai/client.py")
rn = rd("backend/app/ai/runner.py")
dim = rd("backend/app/rubric/dimensions.py")
comp = rd("backend/app/rubric/compute.py")
sc = rd("backend/app/ai/prompts/score.v1.md")
guards = rd("backend/app/core/guards.py")
osvc = rd("backend/app/services/outreach.py")
oapi = rd("backend/app/api/v1/outreach.py")
pipe = rd("backend/app/api/v1/pipeline.py")
rep = rd("backend/app/api/v1/replies.py")
conv = rd("backend/app/services/conversation.py")
fb = rd("backend/app/services/feedback.py")
fbp = rd("backend/app/ai/prompts/feedback.v1.md")
aud = rd("backend/app/core/audit.py")
cand = rd("backend/app/api/v1/candidates.py")
bp = rd("backend/tests/eval/bias_probes.py")
src_api = rd("backend/app/api/v1/sourcing.py")
enr = rd("backend/app/jobs/enrichment.py")
jr = rd("backend/app/jobs/runner.py")
seed = rd("backend/app/seed/demo.py")

# ─────────────────────────────────────────────────────────────── P0 scaffold
add("P0", "gitignore excludes .env", ".env" in rd(".gitignore"))
add("P0", ".env not tracked", not re.search(r"(^|/)\.env$", sh("git ls-files"), re.M))
add("P0", "4 startup checks logged", sum(k in main.lower() for k in ["database", "pgvector", "gemini", "gmail"]) >= 4)
add("P0", "/health endpoint", "health" in rd("backend/app/api/v1/health.py").lower())
add("P0", "alembic baseline", ex("backend/alembic/versions/0001_baseline.py"))
add("P0", "ruff config", ex("backend/ruff.toml"))
add("P0", "smoke test", ex("backend/tests/unit/test_smoke.py"))
add("P0", "frontend design tokens", ex("frontend/src/styles/tokens.css"))
add("P0", "standing docs", all(ex(p) for p in ["CLAUDE.md", "docs/prompts/ui-system.md", "docs/prompts/api-contract.md"]))
unk("P0", "branch protection + collaborators accepted (GitHub-side)")

# ─────────────────────────────────────────────────────────────── P1 schema
for t in ["organizations", "users", "requisitions", "candidates", "candidate_research",
          "pipeline_entries", "outreach_messages", "replies", "feedback_reports",
          "knowledge_chunks", "audit_events", "jobs"]:
    add("P1", f"table {t}", f'"{t}"' in models)
add("P1", "pipeline unique(requisition, candidate)", "UniqueConstraint" in models)
add("P1", "audit append-only revoke in migration",
    "REVOKE" in (rd("backend/alembic/versions/0002_domain_schema.py") +
                 rd("backend/alembic/versions/0003_response_gate_and_pgvector.py")).upper())
add("P1", "JWT security module", "jwt" in rd("backend/app/core/security.py").lower())
add("P1", "require_scope dependency", "require_scope" in rd("backend/app/core/deps.py"))
add("P1", "Gmail OAuth service", "refresh_token" in rd("backend/app/services/gmail.py"))
add("P1", "org_id on business tables", models.count("org_id") >= 10)

# ─────────────────────────────────────────────────────────────── P2 JD parsing
add("P2", "single Gemini adapter", "genai" in cl)
add("P2", "runner validates + retries once", "ValidationError" in rn and "retry" in rn.lower())
add("P2", "jd_parse.v1.md", ex("backend/app/ai/prompts/jd_parse.v1.md"))
add("P2", "IdealProfile schema", "IdealProfile" in rd("backend/app/schemas/ai.py"))
add("P2", "POST /{id}/parse", "/{id}/parse" in rd("backend/app/api/v1/requisitions.py"))
add("P2", "editable profile UI", ex("frontend/src/features/requisitions/ParsedProfileEditor.jsx"))
add("P2", "jd parse test", ex("backend/tests/unit/test_jd_parse.py"))
add("P2", "token + latency logged", "input_tokens" in cl and "latency" in cl)

# ─────────────────────────────────────────────────────────────── P3 sourcing
add("P3", "job runner + jobs table", "job" in jr.lower() and '"jobs"' in models)
add("P3", "commit per item", "commit" in rd("backend/app/jobs/sourcing.py"))
add("P3", "three sourcing paths", all(p in src_api for p in ["/csv", "/urls", "/rizeos-pool"]))
add("P3", "202 + job_id", "ACCEPTED" in src_api or "202" in src_api)
add("P3", "SSRF guard test", ex("backend/tests/unit/test_ssrf_guard.py"))
add("P3", "DNS-resolving SSRF guard", "getaddrinfo" in enr and "is_private" in enr)
add("P3", "robots.txt respected", "robots" in enr.lower())
add("P3", "timeout + size cap", "timeout" in enr and "1024" in enr)
add("P3", "citations validated against fetched pages", "fetched_urls_set" in enr)
add("P3", "GET /jobs/{id}", "jobs" in rd("backend/app/api/v1/jobs.py").lower())

# ─────────────────────────────────────────────────────────────── P4 scoring
add("P4", "5 dimensions, weights assert to 1.0", dim.count("Dimension(") >= 5 and "assert" in dim)
add("P4", "compute_fit_score is pure python", "def compute_fit_score" in comp and "genai" not in comp)
add("P4", "confidence + must-have caps", "70" in comp and "60" in comp)
add("P4", "INVARIANT 1: prompt forbids overall score", "Do NOT produce an overall score" in sc)
add("P4", "citations required", "source_url" in sc and "cite" in sc.lower())
add("P4", "could_not_determine required", "could_not_determine" in sc)
add("P4", "protected attributes excluded", "have not been given" in sc or "do not ask for them" in sc.lower())
add("P4", "GET /{id}/explain", "/{id}/explain" in pipe)
add("P4", "ScoreBadge clickable", "onClick" in rd("frontend/src/components/ui/ScoreBadge.jsx"))
add("P4", "EvidenceDrawer", ex("frontend/src/components/ui/EvidenceDrawer.jsx"))
add("P4", "compute unit test", ex("backend/tests/unit/test_compute_fit_score.py"))
add("P4", "scoring eval harness", ex("backend/tests/eval/scoring_eval.py"))

# ─────────────────────────────────────────────────────────────── P5 outreach
send_fn = body_after(osvc, "def send_outreach_message")
add("P5", "draft/approve/send are separate", "approve" in oapi and "send" in oapi and "/{id}/draft" in pipe)
add("P5", "INVARIANT 2: 409 unless approved", "require_approved" in guards and "409" in guards)
add("P5", "send re-checks approval then contactability",
    "require_approved" in send_fn and "assert_contactable" in send_fn
    and send_fn.index("require_approved") < send_fn.index("assert_contactable"))
add("P5", "outreach.v1.md", ex("backend/app/ai/prompts/outreach.v1.md"))
add("P5", "bulk send-approved", "send-approved" in rd("backend/app/api/v1/requisitions.py"))
add("P5", "review queue UI", ex("frontend/src/features/outreach/OutreachReviewQueue.jsx"))
add("P5", "ApprovalBar", ex("frontend/src/components/ui/ApprovalBar.jsx"))
add("P5", "guards unit test", ex("backend/tests/unit/test_guards.py"))
add("P5", "no approval-bypass flag", not re.search(r"send_immediately|auto_send|skip_approval", osvc + oapi))

# ─────────────────────────────────────────────────────────────── P6 replies
add("P6", "reply.v1.md", ex("backend/app/ai/prompts/reply.v1.md"))
add("P6", "respond.v1.md", ex("backend/app/ai/prompts/respond.v1.md"))
add("P6", "POST /replies/sync", "/sync" in rep)
add("P6", "POST /replies/{id}/classify", "classify" in rep)
add("P6", "POST /replies/{id}/draft-response", "draft-response" in rep)
add("P6", "POST /replies/{id}/approve", '"/{id}/approve"' in rep)
add("P6", "POST /replies/{id}/send", '"/{id}/send"' in rep)
add("P6", "INVARIANT 2 on responses", "require_response_approved" in conv and "require_response_approved" in guards)
add("P6", "retrieval gate closes when nothing relevant", "retrieval_gate_open" in conv)
add("P6", "knowledge_used recorded by app not model", "knowledge_used" in conv)
add("P6", "response gate test", ex("backend/tests/unit/test_response_gate.py"))
add("P6", "TriageInbox wired to real endpoints", "draft-response" in rd("frontend/src/features/replies/TriageInbox.jsx"))

# ─────────────────────────────────────────────────────────────── P7 feedback
add("P7", "feedback.v1.md", ex("backend/app/ai/prompts/feedback.v1.md"))
add("P7", "input is the validated breakdown", "breakdown" in fb.lower())
add("P7", "role-relative framing enforced", "role-relative" in fbp.lower() or "ROLE-RELATIVE" in fbp)
add("P7", "no hiring decision implied", "decision" in fbp.lower())
add("P7", "generate endpoint", "feedback/generate" in pipe)
add("P7", "release endpoint", "feedback/release" in pipe)
add("P7", "bulk release-all", "feedback/release-all" in rd("backend/app/api/v1/requisitions.py"))
add("P7", "GET /me/feedback", "/me/feedback" in rd("backend/app/api/v1/feedback.py"))
add("P7", "release checks do-not-contact", "assert_contactable" in fb)
add("P7", "candidate portal", ex("frontend/src/features/portal/CandidatePortal.jsx"))
add("P7", "recruiter release queue", ex("frontend/src/features/feedback/RecruiterReleaseQueue.jsx"))
add("P7", "fidelity eval", ex("backend/tests/eval/feedback_fidelity.py"))

# ─────────────────────────────────────────────────────────────── P8 safety
wa = body_after(aud, "def write_audit")
wa_code = strip_docstrings(wa)
all_audit = "".join(
    rd(f"backend/app/api/v1/{f}.py") + rd(f"backend/app/services/{f}.py") + rd(f"backend/app/jobs/{f}.py")
    for f in ["requisitions", "pipeline", "outreach", "feedback", "candidates", "sourcing",
              "scoring", "conversation", "credential", "enrichment", "knowledge", "auth"]
)
actions = set(re.findall(r'action="([a-z_]+)"', all_audit))
add("P8", "bias probes: 12 matched pairs", bp.count('"attr"') >= 12 or bp.count("'attr'") >= 12)
add("P8", "probe asserts delta <= 3", "delta <= 3" in bp)
add("P8", "CI workflow exists", ex(".github/workflows/ci.yml"))
add("P8", "CI runs evals as a gate", "bias_probes" in rd(".github/workflows/ci.yml"))
add("P8", "CI asserts both invariants", "Invariant #1" in rd(".github/workflows/ci.yml") and "Invariant #2" in rd(".github/workflows/ci.yml"))
add("P8", "write_audit helper", "def write_audit" in aud)
add("P8", "audit joins caller transaction (no self-commit)", "db.add(event)" in wa and "db.commit()" not in wa_code)
add("P8", f"audit wired on >=8 action families (found {len(actions)})", len(actions) >= 8)
add("P8", "do-not-contact irreversible", "409" in cand or "irreversible" in cand.lower())
add("P8", "data export endpoint", "data-export" in cand)
add("P8", "data deletion endpoint", "/data" in cand and "delete" in cand.lower())
add("P8", "audit viewer UI", ex("frontend/src/features/admin/AuditTrailViewer.jsx"))

# ─────────────────────────────────────────────────────────────── P9 stretch
add("P9", "interview prompt", ex("backend/app/ai/prompts/interview.v1.md"))
add("P9", "interview service", ex("backend/app/services/interview.py"))
add("P9", "credential hashing", "sha256" in rd("backend/app/services/credential.py").lower())
add("P9", "public verify endpoint", "verify" in rd("backend/app/api/v1/credentials.py"))
add("P9", "verification page", ex("frontend/src/features/portal/CredentialVerification.jsx"))
add("P9", "only a hash is anchored", "payload_hash" in rd("backend/app/services/credential.py"))
add("P9", "credential issue audited", "credential_issued" in rd("backend/app/services/credential.py"))

# ─────────────────────────────────────────────────────────────── P10 demo
add("P10", "seed module", ex("backend/app/seed/demo.py"))
add("P10", "--reset flag", "reset" in rd("backend/app/seed/__main__.py") + seed)
add("P10", "40 synthetic candidates", "40" in seed)
add("P10", "score spread across bands", "Low" in seed and "High" in seed)
add("P10", "replies seeded", "reply" in seed.lower())
add("P10", "demo script", ex("docs/demo-script.md"))
add("P10", "README", ex("README.md"))
add("P10", "verification script", ex("scripts/verify.sh"))
unk("P10", "three rehearsals completed")
unk("P10", "backup video recorded")
unk("P10", "deployed to Vercel/Render")

# ─────────────────────────────────────────────────────────────── infra extras
add("INFRA", "dialect-aware vector column", ex("backend/app/core/vector.py"))
add("INFRA", "pgvector migration", ex("backend/alembic/versions/0003_response_gate_and_pgvector.py"))
add("INFRA", "hybrid semantic + keyword search", "SEMANTIC_WEIGHT" in rd("backend/app/services/knowledge.py"))
add("INFRA", "knowledge router registered", "knowledge_router" in rd("backend/app/api/v1/api_router.py"))
add("INFRA", "mock mode surfaced in /health", "ai_mode" in rd("backend/app/api/v1/health.py"))
add("INFRA", "mock mode warned at startup", "AI MOCK MODE ACTIVE" in main)
add("INFRA", "mock flagged on every AI result", "mock: bool" in cl)
add("INFRA", "environment banner in UI", ex("frontend/src/components/ui/EnvironmentBanner.jsx"))

# ─────────────────────────────────────────────────────────────── report
WEIGHT = {"P0": 1, "P1": 1.5, "P2": 1, "P3": 1.5, "P4": 2, "P5": 1, "P6": 1,
          "P7": 1.5, "P8": 1, "P9": 0.5, "P10": 1, "INFRA": 0.5}

print(f"\n{'PHASE':<7}{'PASS':>6}{'FAIL':>6}{'N/A':>5}{'':>4}{'SCORE':>7}   outstanding")
print("─" * 78)
tw = tp = 0.0
total_fail = 0
for ph in ["P0", "P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "INFRA"]:
    items = checks[ph]
    p = sum(1 for _, s in items if s == 1)
    f = sum(1 for _, s in items if s == 0)
    u = sum(1 for _, s in items if s == -1)
    total_fail += f
    pct = 100 * p / (p + f) if (p + f) else 100.0
    tw += WEIGHT[ph]
    tp += WEIGHT[ph] * pct / 100
    fails = [lbl for lbl, s in items if s == 0]
    tail = "; ".join(fails[:2]) + (" …" if len(fails) > 2 else "") if fails else "—"
    print(f"{ph:<7}{p:>6}{f:>6}{u:>5}{'':>4}{pct:>6.0f}%   {tail}")

print("─" * 78)
print(f"\n  Specified surface complete: {100 * tp / tw:.0f}%")
print("  (static check — run scripts/verify.sh to prove it actually runs)\n")
sys.exit(1 if total_fail else 0)
