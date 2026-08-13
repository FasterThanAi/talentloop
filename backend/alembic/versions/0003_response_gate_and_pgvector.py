"""P6 response approval gate + real pgvector embedding column

Two changes:

1. Replies gain a response approval gate (draft -> approved -> sent), so a drafted
   response to a candidate passes the same Invariant #2 check as outreach.

2. On PostgreSQL, `knowledge_chunks.embedding` becomes a real `vector(N)` column with an
   ivfflat cosine index, and the `vector` extension is created. On SQLite the column stays
   JSON and this step is a no-op, so local dev keeps working.

Revision ID: 0003_response_gate_and_pgvector
Revises: 0002_domain_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_response_gate_and_pgvector"
down_revision = "0002_domain_schema"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 768


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    # ---- 1. Response approval gate on replies -------------------------------------
    with op.batch_alter_table("replies") as batch:
        batch.add_column(
            sa.Column("response_status", sa.String(20), nullable=False, server_default="none")
        )
        batch.add_column(sa.Column("response_approved_by", sa.String(36), nullable=True))
        batch.add_column(sa.Column("response_approved_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("response_sent_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index("ix_replies_response_status", "replies", ["response_status"])

    # ---- 2. pgvector, PostgreSQL only ---------------------------------------------
    if _is_postgres():
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Existing rows hold JSON arrays; cast through text so the migration is idempotent
        # on an empty table and correct on a populated one.
        op.execute(
            f"""
            ALTER TABLE knowledge_chunks
            ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM})
            USING CASE
                WHEN embedding IS NULL THEN NULL
                ELSE (embedding #>> '{{}}')::vector({EMBEDDING_DIM})
            END
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_cosine
            ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
            """
        )
        # Re-assert append-only on audit_events. Harmless if 0002 already did it, and it
        # guarantees the guarantee actually exists on whichever database is live.
        op.execute("REVOKE UPDATE, DELETE ON audit_events FROM PUBLIC")


def downgrade() -> None:
    if _is_postgres():
        op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_cosine")
        op.execute(
            "ALTER TABLE knowledge_chunks ALTER COLUMN embedding TYPE jsonb USING to_jsonb(embedding::text)"
        )

    op.drop_index("ix_replies_response_status", table_name="replies")
    with op.batch_alter_table("replies") as batch:
        batch.drop_column("response_sent_at")
        batch.drop_column("response_approved_at")
        batch.drop_column("response_approved_by")
        batch.drop_column("response_status")
