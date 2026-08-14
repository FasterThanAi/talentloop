# TalentLoop — 3-Minute Demo Video Script

**Speaker:** Priyanshu Kumar · **Team 000** — Pranav Somnath Undirkalle, Vineet Ramayya Polampalli, Raj Gautam, Priyanshu Kumar
**Format:** screen recording with voiceover · **Target length:** 2:50–3:00

> **Say the team name once, at the very start, in one line.** Judges match videos to submissions
> by team name, so leaving it out costs you. Don't spend more than 8 seconds on it — no long
> member-by-member introductions, no "first of all we would like to thank". One sentence, then
> straight into the product.

---

## Before you hit record

- [ ] Open the health check link **2 minutes early** and wait for JSON — the free Render tier
      sleeps, and a cold start on camera is 40 seconds of dead air
- [ ] Log in as `demo@talentloop.dev` already, so no password typing on camera
- [ ] Have **two requisitions** ready: one unparsed (to parse live) and one already parsed and
      scored (your backup if the live call is slow)
- [ ] Run the scoring job once beforehand so candidates already have scores — on camera you
      click the button, then cut to the finished result
- [ ] Close every other tab, hide the bookmarks bar, and use a clean browser window
- [ ] Never show `.env`, Render environment variables, or the Google console — API keys on
      screen is an instant problem
- [ ] Browser zoom 110%, record at 1080p, and do one silent practice run first

---

## The script

Timings are a guide. Speak normally — if you're 10 seconds over, that's fine.

### 0:00 – 0:12 · Intro
**On screen:** the recruiter dashboard, already logged in.

> "Hi, I'm Priyanshu from Team 000 — with Pranav, Vineet and Raj. We built TalentLoop, an AI
> hiring assistant that scores candidates using evidence you can actually check."

---

### 0:12 – 0:30 · The problem
**On screen:** stay on the dashboard, slowly scroll the requisition list.

> "Here's the problem we started with. One job post gets hundreds of applicants. Recruiters read
> the first forty and stop. And everyone who gets rejected just hears nothing back. We wanted to
> fix both sides of that."

---

### 0:30 – 0:55 · Parse the job description
**On screen:** open a requisition → **Raw Job Description** tab → click **Parse Job Description**.

> "This is a job requisition. Here's the raw job description the recruiter pasted in. When I
> click parse, the model turns it into a structured profile — must-haves, nice-to-haves,
> seniority, domain. And the recruiter can edit every single field, so nothing gets decided
> silently behind their back."

*If parsing takes more than ~6 seconds, cut to the parsed profile you prepared earlier.*

---

### 0:55 – 1:20 · Sourcing and evidence
**On screen:** go to **Pipeline**, scroll the candidate list.

> "Now the pipeline. These candidates came from a CSV upload, public profile links, or the
> RizeOS pool — nothing scraped from anywhere it shouldn't be. For each person we read their
> public pages and pull out real evidence: their skills, their projects, and the URL that each
> piece of evidence came from."

---

### 1:20 – 1:55 · The score — your strongest 30 seconds
**On screen:** click **Score All Candidates**, then open one candidate's evidence drawer. Scroll
slowly through the five dimensions so the citations are visible.

> "I'll run the scoring — and open one candidate. This next part is the whole point of our
> project. The model did **not** produce this number. It rated five dimensions separately, and
> it had to cite evidence for each rating. Must-have coverage is forty percent, depth of
> experience twenty-five, and so on. Python does the weighted maths at the end. So the score is
> repeatable, and if a recruiter disagrees with the weights, they change a number in a rubric
> file — they don't re-prompt a black box."

*Slow down here. Let the citations stay on screen for a beat.*

---

### 1:55 – 2:20 · The approval gate
**On screen:** click **Draft** on that candidate → show the generated email → point at the
disabled **Send** button → click **Approve** → **Send** becomes enabled.

> "From here the model drafts outreach that references something the candidate actually built —
> not a template. But look at the Send button: it's disabled. It only turns on after a human
> clicks Approve. Nothing in this system emails a real person on its own, and every approval
> gets written to an audit log."

---

### 2:20 – 2:45 · Candidate feedback
**On screen:** switch to the **Candidate Portal** (second browser profile or incognito, logged
in as `alex.rivera@synth.dev`). Show the feedback report.

> "And this is the part we care about most. This candidate didn't make the shortlist. Instead of
> silence, they log into the portal and get this — where they were strong, what evidence was
> missing, and what they can actually do about it. The recruiter still has to release it
> deliberately. Nobody gets auto-rejected by a machine."

---

### 2:45 – 3:00 · Close
**On screen:** the health check endpoint, or the dashboard again.

> "Everything you saw is running live — FastAPI on Render, React on Vercel, Postgres on
> Supabase, with Gemini and a Groq fallback so it doesn't die on a rate limit. Bias checks and
> both of those rules are enforced in our CI. Everything's in the README. Thanks for watching."

---

## Delivery notes

- **Don't read this word for word.** Learn the order of the six beats, then say it in your own
  words. Slightly imperfect but natural beats a perfect robot read.
- **Talk about what's on screen as you click**, not before it. Silence while a page loads is
  much better than describing something the judge can't see yet.
- **Contractions are fine** — "we've", "it's", "doesn't". You're a student showing your project,
  not narrating a corporate ad.
- **Don't apologise** for the free tier being slow, for the UI, or for anything else. Just don't
  record the slow bits.
- **The two lines that must survive**, even if you cut everything else:
  1. "The model did not produce this number."
  2. "Nothing gets sent without a human approving it."
- If you fumble a sentence, pause for two seconds and say it again — that gives you a clean cut
  point in editing.

## If something breaks mid-recording

| Problem | What to do |
|---|---|
| AI call is slow or 429s | Stop, cut, use the pre-scored requisition. Don't narrate the wait. |
| Backend cold-started | Open the health link, wait for JSON, restart the recording |
| Score shows "(Unscored)" | The job description wasn't parsed — parse it, then score again |
| You go over 3 minutes | Cut the problem section (0:12–0:30) first; the product speaks for itself |
