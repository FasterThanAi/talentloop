# TalentLoop — UI System

Apply this to every frontend change. If a requested design conflicts with these rules, follow
these rules and say so.

## Product personality
Calm, evidential, trustworthy. This is a tool that judges people, so the interface must feel
accountable rather than clever. Think clinical dashboard, not consumer app. No gradients on
surfaces, no decorative illustration, no emoji in product UI, no motion longer than 200ms.
Whitespace and typographic hierarchy do the work.

## Design tokens — the ONLY values allowed
Define once in `src/styles/tokens.css` and reference through Tailwind config. Never hardcode a hex.

Colour
  --bg              #FFFFFF     page background
  --surface         #F7F9FC     cards, table headers, inset panels
  --border          #E2E8F0     all hairlines
  --text            #0F172A     primary text
  --text-muted      #64748B     secondary text, labels, captions
  --primary         #2563EB     actions, links, focus ring
  --primary-weak    #EFF4FF     selected rows, info callouts
  --success         #0F7A5A     approved, sent, passing checks
  --warning         #B45309     needs review, low confidence
  --danger          #B91C1C     destructive, do-not-contact, failed
  --evidence        #6D28D9     AI-generated content and citations (see below)

Score bands — used consistently everywhere a fit score appears
  80–100  --success      strong evidence of fit
  60–79   #2563EB        partial fit, gaps named
  40–59   --warning      weak fit
  0–39    --text-muted   not a fit  (NEVER --danger: a low score is not an error or a rejection)

Type    Inter (system-ui fallback). 12 / 14 / 16 / 20 / 28px. Weights 400, 500, 600 only.
Space   4px scale: 4 8 12 16 24 32 48. Nothing between.
Radius  6px controls, 10px cards, 999px pills.
Shadow  One elevation only: 0 1px 2px rgb(15 23 42 / 0.06). No other shadows.

## The evidence rule — the most important UI rule in this product
Anything a model generated or inferred is visually distinguishable from anything a human entered
or a source stated. AI-generated content carries a subtle --evidence left border or label chip.
Every fit score renders as `<ScoreBadge>` and every ScoreBadge is clickable, opening the evidence
drawer with the rubric breakdown, per-dimension reasoning, cited source links, declared confidence
and the "could not determine" list. There is no code path that displays a bare number.

## Component inventory — build these once, reuse everywhere
Put them in `src/components/ui/`. Do not create a one-off variant inside a feature folder.

  AppShell          sidebar + topbar + content; owns page title and breadcrumb
  PageHeader        title, subtitle, primary action slot
  DataTable         sortable, cursor-paginated, row selection, sticky header,
                    built-in loading / empty / error states
  ScoreBadge        0–100 pill, band-coloured, always clickable → EvidenceDrawer
  EvidenceDrawer    right-side panel: dimension bars, reasoning, source links,
                    confidence, could-not-determine list
  StatusPill        draft | approved | sent | replied | released | needs_review
  ApprovalBar       sticky bottom bar for bulk approve/reject; shows exact count
                    and requires a second click for anything over 20 items
  ConfidenceMeter   low / medium / high with the reason on hover
  EmptyState        icon, one-line explanation, one action
  JobProgress       polls a job_id, shows processed/total and per-item errors
  ConfirmDialog     required for every irreversible action; types the noun to confirm

## Layout rules
- Max content width 1280px, centred. Tables may go full-bleed inside that.
- One primary action per screen. Everything else is secondary or lives in a menu.
- Destructive actions are never adjacent to primary actions.
- Forms are single-column. Labels above inputs. Inline validation on blur, never on keystroke.

## State handling — all four, every time
Loading  skeleton rows matching the real layout, never a centred spinner
Empty    EmptyState explaining what would appear here and how to make it appear
Error    what failed, in plain language, plus a retry affordance. Never a raw stack trace.
Success  the data. If it took over 3 seconds, say what happened.

## Accessibility floor
Keyboard reachable for every interactive element; visible focus ring using --primary.
4.5:1 contrast on all text. Colour is never the only signal — score bands carry a number,
statuses carry a word. Drawers and dialogs trap focus and close on Escape.

## Never
- Never invent a colour, radius, shadow or font size outside the tokens.
- Never show a score without a path to its reasoning.
- Never use red for a low score.
- Never auto-refresh a list a user is actively reading.
- Never put a bulk destructive action behind a single click.
- Never render AI-generated text identically to human-entered text.
