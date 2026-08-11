from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: str
    why_required: str
    evidence_of: str


class IdealProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_title: str
    seniority: Literal["intern", "junior", "mid", "senior", "lead", "principal"]
    must_have_skills: list[SkillRequirement] = Field(default_factory=list)
    nice_to_have_skills: list[SkillRequirement] = Field(default_factory=list)
    domain_context: str
    location_constraint: str | None = None
    implicit_signals: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: str | None = None
    signal: str | None = None
    name: str | None = None
    what_it_does: str | None = None
    evidence_quote: str
    source_url: str


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    skills: list[EvidenceClaim] = Field(default_factory=list)
    seniority_signals: list[EvidenceClaim] = Field(default_factory=list)
    projects: list[EvidenceClaim] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    could_not_determine: list[str] = Field(default_factory=list)


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: str
    score: int = Field(ge=0, le=100)
    justification: str
    citations: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimensions: list[DimensionScore]
    could_not_determine: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]
    risk_flags: list[str] = Field(default_factory=list)


class OutreachDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str
    body: str
    specific_reference_used: str


class ReplyClassification(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Literal[
        "interested",
        "not_interested",
        "needs_info",
        "salary_question",
        "schedule_request",
        "referral",
        "auto_reply",
        "unclear"
    ]
    sentiment: Literal["positive", "neutral", "negative"]
    priority: Literal["high", "medium", "low"]
    summary: str
    suggested_action: str


class ResponseDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str
    knowledge_used: list[str] = Field(default_factory=list)
    deferred_questions: list[str] = Field(default_factory=list)


class FeedbackPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    point: str
    dimension: str | None = None
    supporting_evidence_ref: str | None = None
    why_it_mattered: str | None = None


class FeedbackReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fit_summary: str
    strengths: list[FeedbackPoint] = Field(default_factory=list)
    gaps: list[FeedbackPoint] = Field(default_factory=list)
    improve_advice: list[str] = Field(default_factory=list)


class InterviewQuestionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    question: str
    targeting_gap: str


class InterviewQuestions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[InterviewQuestionItem]


class FollowUpQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    follow_up_question: str
    probing_reason: str
