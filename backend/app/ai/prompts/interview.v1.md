You are designing 3 to 5 open, specific, written interview questions to help a candidate provide context that their public profile or resume did not contain.

ROLE
{{ideal_profile}}

NAMED GAPS FROM EVALUATION
{{named_gaps}}

Rules:
- Questions must specifically target the missing evidence/gaps above.
- Questions should be answerable in a short paragraph (2-4 sentences).
- Frame questions constructively: "Tell us about a time you worked with X..." or "How did you approach Y in your projects?"
- Do NOT make it a trivia test. Capture context, experience, and approach.

Return only JSON:
{
  "questions": [
    {"id": "q1", "question": "...", "targeting_gap": "..."},
    {"id": "q2", "question": "...", "targeting_gap": "..."}
  ]
}
