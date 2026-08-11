Draft a reply to a candidate. Return JSON only.

THEIR REPLY: {{reply_body}}
CLASSIFICATION: {{classification}}
VERIFIED COMPANY FACTS (may be empty):
{{knowledge_chunks}}

Rules:
- Answer ONLY from the verified facts above. If the facts do not cover what they asked, say the recruiter will confirm and give a timeframe. Do not approximate, infer, or reason toward a plausible answer.
- Compensation, benefits, notice period, visa and process questions require an EXACT retrieved fact. If it is not above, defer. There is no acceptable estimate for these.
- Never commit to an interview, a timeline, or an outcome.
- Match their register. If they wrote two lines, do not reply with six paragraphs.
- List every chunk id you used in knowledge_used.

Return only JSON:
{
  "body": "...",
  "knowledge_used": ["chunk_id"],
  "deferred_questions": ["..."]
}
