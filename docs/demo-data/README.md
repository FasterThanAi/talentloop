# Demo data pack

Everything needed to run TalentLoop end to end — new requisition through to a candidate
reading their feedback report — with five student candidates.

| File | What it is |
|---|---|
| `job-description.md` | The JD to paste into a new requisition |
| `candidates.csv` | Five student candidates with public GitHub profiles |

## Why these candidates

The four teammates' own GitHub profiles are used deliberately. They are real public pages, so
enrichment finds genuine evidence and the scores mean something — and there is no question of
putting a stranger's data in a public demo video.

Want a fifth? Add a row with another account you actually own. Do not invent a URL: a profile
that does not exist produces an empty evidence set and a meaningless low score, which is the
one thing you do not want on camera.

The CSV columns match what the parser accepts: `name`, `email`, `urls` (semicolon-separated if
a candidate has more than one link).

## Run order

Do this once as a rehearsal, then again on camera.

**1. Create the requisition** *(no AI call)*
Requisitions → New Requisition. Title: `Full-Stack Product Engineer (Intern / New Grad)`.
Paste the JD from `job-description.md`.

**2. Parse the job description** *(1 AI call, ~5–15s)*
Click **Parse Job Description**. Edit one field afterwards so it is visibly yours to control —
adding a nice-to-have works well on camera.

**3. Upload the candidates** *(no AI call for sourcing)*
Source Candidates → CSV → `candidates.csv`. Five candidates enter the pipeline.

**4. Wait for enrichment** *(5 AI calls, ~30–60s)*
Enrichment chains automatically after sourcing. Wait until each candidate shows evidence and
verified source URLs before scoring — scoring a candidate with no evidence produces a low,
unconvincing result.

**5. Score everyone** *(10 AI calls, ~60–120s)*
Requisition → **Score All Candidates**. Each candidate costs two calls: the rubric score and
the auto-drafted feedback report.

**6. Draft outreach for the top candidate** *(1 AI call)*
Pipeline → **Draft** on the highest scorer.

**7. Approve it**
Outreach Gate → confirm Send is unavailable → **Approve Draft** → Send becomes available.

**8. Release feedback for a lower scorer**
Feedback Release → pick someone mid-table → **Release**.

**9. Read it as the candidate**
Log in as that candidate in a private window and open the portal.

**Total: about 17 AI calls.** On Gemini's free tier (20/day) that is one full run and nothing
left over. Set `AI_PROVIDER_ORDER=groq,gemini` on Render before rehearsing, so Groq carries
the load and Gemini stays as the untouched fallback.

## Candidate accounts for the portal

The portal matches a candidate's login email against the candidate record. To show a
teammate's report rather than the seeded one, register a candidate account with the matching
email first:

| Email | Password | Role at registration |
|---|---|---|
| `priyanshu.demo@talentloop.dev` | your choice | Candidate |
| `raj.demo@talentloop.dev` | your choice | Candidate |

Register at `/register`, choose **Candidate** (no organisation name required), then release
that candidate's feedback report from the recruiter account.

`alex.rivera@synth.dev / password123` already exists from the seed and needs no setup.

## What to have ready before recording

Do a full rehearsal run first. Then, on camera:

- **Do live:** the JD parse (step 2) and the outreach draft + approve (steps 6–7). Both are
  fast and both prove the product is real.
- **Have ready from the rehearsal:** the scored pipeline and a released feedback report, so
  you never film a progress bar.

Say it out loud once when you open the pipeline: *"I scored these earlier so you don't have
to watch the queue."* Judges respect that far more than a demo that quietly hides its waits.

## Resetting between takes

If a run goes wrong, delete the requisition and repeat from step 1 — sourcing dedupes on
email, so re-uploading the same CSV into a *new* requisition is safe, and re-uploading it into
the *same* one correctly skips the existing candidates.
