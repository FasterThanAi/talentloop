# TalentLoop — Git & Team Workflow

**Window:** 10–14 August · 5 days · 4 people
**Repo:** a **brand-new** repository. Proven modules are ported by hand from prior project; nothing is branched, imported or merged from it.

## Roles
| Person | Role | Owns |
|---|---|---|
| **Priyanshu** | Repo owner / integrator | Repo creation, scaffold, branch protection, P0 + P1, final merges, deployment |
| **Member B** | Ingestion | P2 (JD parsing) + P3 (sourcing & enrichment) |
| **Member C** | Intelligence | P4 (scoring) + P8 (bias & audit) |
| **Member D** | Experience | P7 (feedback report + candidate portal) + UI component library |
| *Rotating* | Outreach | P5 + P6 (outreach, approval gate, reply triage) |

## Daily Loop
1. Branch from `main`: `git checkout -b p4-fit-scoring`
2. Build, test, run acceptance checks.
3. Merge `main` into branch before pushing.
4. Open PR with checklist.
5. Squash merge to `main`.
