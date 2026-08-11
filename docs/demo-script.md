# TalentLoop — 5-Minute Demo Script & Run Sheet

**Theme:** Ethical AI & Responsible Innovation  
**Time Limit:** 5:00 minutes  
**Goal:** Prove the two invariants, show the explainability and candidate feedback differentiator, and demonstrate fairness gates.

---

## Demo Schedule & Speaking Points

| Time | What to Show | What to Say | Fallback if Network Fails |
|---|---|---|---|
| **0:00 - 0:30** | *Presenter speaking* | "A recruiter spends about six seconds on a resume. That is not evaluation; it is keyword triage. And rejected candidates receive total silence. TalentLoop is an agentic hiring assistant that changes both sides of that equation." | None needed |
| **0:30 - 1:00** | **Requisition View** (`/requisitions`) with parsed profile | "We parse the job description into what the team actually needs — including implicit signals a keyword filter throws away. The recruiter can inspect and edit every field." | Pre-seeded requisition |
| **1:00 - 1:45** | **Ranked Candidate Pipeline** (`/pipeline`) | "40 candidates sourced from consent-safe channels only — zero LinkedIn scraping. Every candidate is researched against public evidence." | Pre-seeded 40 candidates |
| **1:45 - 2:30** | **Evidence Drawer & ScoreBadge** (Click score 92) | "Every fit score opens in one click. Five dimensions, each cited to verifiable source URLs. **Invariant 1: The language model never produced this number.** It rated dimensions; deterministic Python did the arithmetic." | Pre-seeded breakdown |
| **2:30 - 3:15** | **Outreach & Approval Gate** (`/outreach`) | "The model drafts personalized outreach grounded in candidate evidence. **Invariant 2: It never sends automatically.** Approval is a distinct API action, audited and non-bypassable." | Show pre-sent message in seed |
| **3:15 - 4:00** | **Candidate Portal & Feedback Report** (`/portal`) | "This candidate did not make the shortlist. Here is what they receive instead of silence: role-relative fit, evidenced strengths, named missing evidence, and actionable improvement steps. They keep this report with cryptographic verification." | Log in as `alex.rivera@synth.dev` |
| **4:00 - 4:35** | **Matched-Pair Bias Probes & Audit** (`/admin`) | "Twelve matched candidate pairs with protected attributes varied. Zero score delta because demographic fields never enter the scoring payload. This is a CI build gate, not a slide claim." | Pre-run probe table |
| **4:35 - 5:00** | **Closing** | "Better-evidenced automation, not more automation. A human on every decision that touches a person — and the candidate leaves with something they own." | None needed |

---

## Quick Reset Command
Between rehearsal runs, reset and re-seed the environment in under 10 seconds:
```bash
cd backend
python -m app.seed --reset --demo
```
