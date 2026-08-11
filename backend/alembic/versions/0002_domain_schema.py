"""0002_domain_schema

Revision ID: 0002_domain_schema
Revises: 0001_baseline
Create Date: 2026-08-11 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_domain_schema'
down_revision: Union[str, None] = '0001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # 1. organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('plan', sa.String(50), server_default="standard"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 2. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default="recruiter"),
        sa.Column('gmail_refresh_token_encrypted', sa.Text(), nullable=True),
        sa.Column('gmail_email', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_users_org_id', 'users', ['org_id'])
    op.create_index('ix_users_email', 'users', ['email'])

    # 3. requisitions
    op.create_table(
        'requisitions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('jd_raw', sa.Text(), nullable=False),
        sa.Column('parsed_profile', sa.JSON(), nullable=True),
        sa.Column('seniority', sa.String(50), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), server_default="draft"),
        sa.Column('rizeos_job_id', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_requisitions_org_id', 'requisitions', ['org_id'])

    # 4. candidates
    op.create_table(
        'candidates',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('source', sa.String(50), server_default="manual"),
        sa.Column('public_urls', sa.JSON(), nullable=False),
        sa.Column('consent_status', sa.String(50), server_default="none"),
        sa.Column('do_not_contact', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_candidates_org_email', 'candidates', ['org_id', 'email'])

    # 5. candidate_research
    op.create_table(
        'candidate_research',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.String(36), sa.ForeignKey('candidates.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('skills', sa.JSON(), nullable=False),
        sa.Column('seniority_signals', sa.JSON(), nullable=False),
        sa.Column('projects', sa.JSON(), nullable=False),
        sa.Column('evidence_urls', sa.JSON(), nullable=False),
        sa.Column('confidence', sa.String(20), server_default="medium"),
        sa.Column('could_not_determine', sa.JSON(), nullable=False),
        sa.Column('researched_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_candidate_research_org_id', 'candidate_research', ['org_id'])

    # 6. pipeline_entries
    op.create_table(
        'pipeline_entries',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('requisition_id', sa.String(36), sa.ForeignKey('requisitions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('candidate_id', sa.String(36), sa.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.String(50), server_default="sourced"),
        sa.Column('fit_score', sa.Integer(), nullable=True),
        sa.Column('score_reason', sa.Text(), nullable=True),
        sa.Column('score_breakdown', sa.JSON(), nullable=True),
        sa.Column('rubric_version', sa.String(20), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('requisition_id', 'candidate_id', name='uq_pipeline_req_candidate')
    )
    op.create_index('ix_pipeline_req_fit_score', 'pipeline_entries', ['requisition_id', 'fit_score'])

    # 7. outreach_messages
    op.create_table(
        'outreach_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pipeline_entry_id', sa.String(36), sa.ForeignKey('pipeline_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel', sa.String(50), server_default="email"),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), server_default="draft"),
        sa.Column('approved_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gmail_message_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_outreach_messages_pipeline', 'outreach_messages', ['pipeline_entry_id'])

    # 8. replies
    op.create_table(
        'replies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outreach_message_id', sa.String(36), sa.ForeignKey('outreach_messages.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raw_body', sa.Text(), nullable=False),
        sa.Column('intent', sa.String(50), nullable=False),
        sa.Column('sentiment', sa.String(20), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('suggested_action', sa.Text(), nullable=False),
        sa.Column('response_draft', sa.JSON(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_replies_outreach_msg', 'replies', ['outreach_message_id'])

    # 9. feedback_reports
    op.create_table(
        'feedback_reports',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pipeline_entry_id', sa.String(36), sa.ForeignKey('pipeline_entries.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('fit_summary', sa.Text(), nullable=False),
        sa.Column('strengths', sa.JSON(), nullable=False),
        sa.Column('gaps', sa.JSON(), nullable=False),
        sa.Column('improve_advice', sa.JSON(), nullable=False),
        sa.Column('score_snapshot', sa.Integer(), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('candidate_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 10. knowledge_chunks
    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', sa.JSON(), nullable=True),
        sa.Column('document_id', sa.String(255), nullable=True),
        sa.Column('chunk_index', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_knowledge_chunks_org_id', 'knowledge_chunks', ['org_id'])

    # 11. audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), nullable=False),
        sa.Column('actor_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('entity', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_audit_events_org_id', 'audit_events', ['org_id'])
    op.create_index('ix_audit_events_entity', 'audit_events', ['entity', 'entity_id'])

    # Revoke UPDATE and DELETE on audit_events for append-only guarantee in Postgres
    if is_postgres:
        op.execute("REVOKE UPDATE, DELETE ON TABLE audit_events FROM PUBLIC;")

    # 12. jobs
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), server_default="queued"),
        sa.Column('processed', sa.Integer(), server_default="0"),
        sa.Column('total', sa.Integer(), server_default="0"),
        sa.Column('errors', sa.JSON(), nullable=False),
        sa.Column('result_ref', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('ix_jobs_org_id', 'jobs', ['org_id'])

    # 13. interview_sessions
    op.create_table(
        'interview_sessions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('pipeline_entry_id', sa.String(36), sa.ForeignKey('pipeline_entries.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('questions', sa.JSON(), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('follow_up_question', sa.Text(), nullable=True),
        sa.Column('follow_up_answer', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), server_default="pending"),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 14. credential_records
    op.create_table(
        'credential_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('org_id', sa.String(36), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('feedback_report_id', sa.String(36), sa.ForeignKey('feedback_reports.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('payload_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('tx_hash', sa.String(66), nullable=True),
        sa.Column('network', sa.String(50), server_default="polygon-amoy"),
        sa.Column('revoked', sa.Boolean(), server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )


def downgrade() -> None:
    op.drop_table('credential_records')
    op.drop_table('interview_sessions')
    op.drop_table('jobs')
    op.drop_table('audit_events')
    op.drop_table('knowledge_chunks')
    op.drop_table('feedback_reports')
    op.drop_table('replies')
    op.drop_table('outreach_messages')
    op.drop_table('pipeline_entries')
    op.drop_table('candidate_research')
    op.drop_table('candidates')
    op.drop_table('requisitions')
    op.drop_table('users')
    op.drop_table('organizations')
