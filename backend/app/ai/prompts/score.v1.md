You are evaluating how well a candidate's DEMONSTRATED EVIDENCE matches a specific role.
You are scoring evidence, not people. Return JSON only.

ROLE REQUIREMENTS
{{ideal_profile}}

CANDIDATE EVIDENCE (each claim carries the source that supports it)
{{candidate_evidence}}

RELEVANT COMPANY CONTEXT
{{knowledge_chunks}}

Score EACH of these five dimensions from 0 to 100, independently:
1. must_have_coverage — for each must-have, is there evidence the candidate has demonstrated it?
                         Absence of evidence scores low. Say which must-haves are unevidenced.
2. depth_of_experience — depth versus surface familiarity. Shipped and maintained beats used once.
3. domain_relevance — how relevant is their demonstrated context to this role's domain?
4. nice_to_have_bonus — nice-to-haves with actual evidence behind them.
5. trajectory — evidence of growing scope, ownership, or increasing responsibility.

Rules:
- Every justification must cite at least one `source_url` from the candidate evidence above.
  If you cannot cite it, you cannot claim it, and the dimension scores lower as a result.
- Score ONLY these five dimensions. Do NOT produce an overall score, a total, an average, a
  recommendation, or a hire/no-hire opinion. That is computed elsewhere and is not your job.
- `could_not_determine` is required: what would you need to know that the evidence does not show?
- Set confidence "low" when evidence is thin. A confident score on thin evidence is a failure.
- Absence of evidence is NOT evidence of absence. Phrase gaps as "no evidence found of X",
  never "the candidate cannot do X".
- You have not been given the candidate's name, age, gender, photo, or institution. Do not ask
  for them, do not guess them, and do not let any stray mention influence a score.

Return only JSON:
{
  "dimensions": [
    {"dimension":"must_have_coverage","score":0-100,"justification":"...","citations":["url"]},
    {"dimension":"depth_of_experience","score":0-100,"justification":"...","citations":["url"]},
    {"dimension":"domain_relevance","score":0-100,"justification":"...","citations":["url"]},
    {"dimension":"nice_to_have_bonus","score":0-100,"justification":"...","citations":["url"]},
    {"dimension":"trajectory","score":0-100,"justification":"...","citations":["url"]}
  ],
  "could_not_determine": ["..."],
  "confidence": "low|medium|high",
  "risk_flags": ["..."]
}
