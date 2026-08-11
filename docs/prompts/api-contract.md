# TalentLoop — API Contract

Apply to every backend change.

## Shape
- Base path `/api/v1`. Plural nouns. Sub-resources nest one level, never two.
- Routers are thin: validate input, check scope, call one service function, return a schema.
  If a router has an `if` about business rules, it belongs in the service.
- Every response is a Pydantic model. Never return a bare dict or an ORM object.

## Auth and tenancy
- `Depends(require_scope("recruiter"))` on every route. There is no unprotected route except
  `/health` and `GET /credentials/{hash}/verify`.
- `org_id` comes from the token and is injected into the session context. Never accept it from
  the client. Never write a query that omits it.
- Candidate-role accounts reach only their own consent state, feedback reports and credentials.

## Long-running work
- Anything that calls a model in a loop returns 202 with `{job_id, status: "queued"}`.
- `GET /jobs/{job_id}` → `{status, processed, total, errors[], result_ref}`.
- Jobs commit after every item. A crash at item 40 of 100 leaves 40 saved and the job resumable.
- Never block a request on a model call. Never raise the HTTP timeout to make something fit.

## Approval-gated actions
Draft, approve and execute are three distinct states and three distinct endpoints:
  POST /pipeline/{id}/draft          → status=draft
  POST /outreach/{id}/approve        → status=approved, records approved_by + timestamp
  POST /outreach/{id}/send           → 409 unless status == approved
The send endpoint re-checks `do_not_contact` immediately before dispatch, not only at draft time.

## Errors
One envelope for everything:
  {"type": "about:blank", "title": "Draft not approved", "status": 409,
   "detail": "Message 41 is in state 'draft'. Approve it before sending.",
   "code": "OUTREACH_NOT_APPROVED"}
`code` is a stable machine-readable string the frontend switches on. Never leak a stack trace,
a SQL fragment, or a raw provider error to the client.

## Lists
Cursor pagination: `?cursor=&limit=` → `{items[], next_cursor}`. Default limit 50, max 200.
Filtering is explicit query params, never a free-form filter object.

## AI endpoints
Every response from an endpoint that called a model includes:
  {"_ai": {"model": "...", "prompt": "score.v1", "input_tokens": n, "output_tokens": n,
           "latency_ms": n}}
This is how we attribute spend per requisition and reproduce any historical result.

## Idempotency
Every mutating endpoint accepts an `Idempotency-Key` header and returns the original response for
a repeated key within 24 hours. Sending an email twice because a user double-clicked is
unacceptable in this product.

## Audit
Every consequential action writes to `audit_events` inside the same transaction as the change:
actor_id, action, entity, entity_id, payload, created_at. The table has no UPDATE or DELETE grant.
If an action is worth a user seeing later, it is worth auditing.
