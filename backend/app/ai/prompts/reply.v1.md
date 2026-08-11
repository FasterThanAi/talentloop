Classify one reply to a recruiting outreach message. Return JSON only. Use only the values listed.

MESSAGE WE SENT: {{outreach_body}}
THEIR REPLY: {{reply_body}}

Rules:
- out-of-office and automated bounces are auto_reply.
- A polite decline is not_interested with neutral sentiment, not negative.
- When genuinely unclear, use unclear — do not guess.

Return only JSON:
{
  "intent": "interested|not_interested|needs_info|salary_question|schedule_request|referral|auto_reply|unclear",
  "sentiment": "positive|neutral|negative",
  "priority": "high|medium|low",
  "summary": "one sentence",
  "suggested_action": "what the recruiter should do next"
}
