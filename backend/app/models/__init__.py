import uuid
from datetime import UTC, datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="standard")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users = relationship("User", back_populates="organization", cascade="all, delete-orphan")
    requisitions = relationship("Requisition", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="recruiter")  # admin | recruiter | candidate
    gmail_refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="users")


class Requisition(Base):
    __tablename__ = "requisitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    jd_raw: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft | parsed | parse_failed | active | closed
    rizeos_job_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization = relationship("Organization", back_populates="requisitions")
    pipeline_entries = relationship("PipelineEntry", back_populates="requisition", cascade="all, delete-orphan")


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")  # csv | urls | rizeos_pool | manual
    public_urls: Mapped[list] = mapped_column(JSON, default=list)  # stored as JSON list of URLs
    consent_status: Mapped[str] = mapped_column(String(50), default="none")  # none | granted | revoked
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        Index("ix_candidates_org_email", "org_id", "email"),
    )

    organization = relationship("Organization", back_populates="candidates")
    research = relationship("CandidateResearch", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    pipeline_entries = relationship("PipelineEntry", back_populates="candidate", cascade="all, delete-orphan")


class CandidateResearch(Base):
    __tablename__ = "candidate_research"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), unique=True, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    seniority_signals: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    evidence_urls: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")  # low | medium | high
    could_not_determine: Mapped[list] = mapped_column(JSON, default=list)
    researched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidate = relationship("Candidate", back_populates="research")


class PipelineEntry(Base):
    __tablename__ = "pipeline_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    requisition_id: Mapped[str] = mapped_column(String(36), ForeignKey("requisitions.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(50), default="sourced")  # sourced | researched | scored | outreach_drafted | contacted | replied | interviewed | feedback_ready | closed
    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rubric_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        UniqueConstraint("requisition_id", "candidate_id", name="uq_pipeline_req_candidate"),
        Index("ix_pipeline_req_fit_score", "requisition_id", "fit_score"),
    )

    requisition = relationship("Requisition", back_populates="pipeline_entries")
    candidate = relationship("Candidate", back_populates="pipeline_entries")
    outreach_messages = relationship("OutreachMessage", back_populates="pipeline_entry", cascade="all, delete-orphan")
    feedback_report = relationship("FeedbackReport", back_populates="pipeline_entry", uselist=False, cascade="all, delete-orphan")
    interview_session = relationship("InterviewSession", back_populates="pipeline_entry", uselist=False, cascade="all, delete-orphan")


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="email")
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft | approved | sent | failed
    approved_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gmail_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pipeline_entry = relationship("PipelineEntry", back_populates="outreach_messages")
    replies = relationship("Reply", back_populates="outreach_message", cascade="all, delete-orphan")


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    outreach_message_id: Mapped[str] = mapped_column(String(36), ForeignKey("outreach_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_body: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(50), nullable=False)  # interested | not_interested | needs_info | salary_question | schedule_request | referral | auto_reply | unclear
    sentiment: Mapped[str] = mapped_column(String(20), nullable=False)  # positive | neutral | negative
    priority: Mapped[str] = mapped_column(String(20), nullable=False)  # high | medium | low
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    response_draft: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    outreach_message = relationship("OutreachMessage", back_populates="replies")


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_entries.id", ondelete="CASCADE"), unique=True, nullable=False)
    fit_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, default=list)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    improve_advice: Mapped[list] = mapped_column(JSON, default=list)
    score_snapshot: Mapped[int] = mapped_column(Integer, nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pipeline_entry = relationship("PipelineEntry", back_populates="feedback_report")
    credential_record = relationship("CredentialRecord", back_populates="feedback_report", uselist=False, cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # role_context | company_policy | salary_bands | benefits
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of floats or pgvector
    document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued")  # queued | processing | completed | failed
    processed: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    result_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    pipeline_entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("pipeline_entries.id", ondelete="CASCADE"), unique=True, nullable=False)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    follow_up_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending | completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    pipeline_entry = relationship("PipelineEntry", back_populates="interview_session")


class CredentialRecord(Base):
    __tablename__ = "credential_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_report_id: Mapped[str] = mapped_column(String(36), ForeignKey("feedback_reports.id", ondelete="CASCADE"), unique=True, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)
    network: Mapped[str] = mapped_column(String(50), default="polygon-amoy")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    feedback_report = relationship("FeedbackReport", back_populates="credential_record")
