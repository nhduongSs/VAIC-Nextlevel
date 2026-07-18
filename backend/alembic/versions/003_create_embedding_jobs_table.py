"""create embedding_jobs table

Revision ID: 003
Revises: 002
Create Date: 2026-07-18

"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE embedding_jobs (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            status          VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
                                status IN (
                                    'PENDING','RUNNING','COMPLETED',
                                    'FAILED','RETRYING','CANCELLED'
                                )
                            ),
            model_name      VARCHAR(200) NOT NULL,
            total_chunks    INTEGER NOT NULL DEFAULT 0,
            embedded_chunks INTEGER NOT NULL DEFAULT 0,
            failed_chunks   INTEGER NOT NULL DEFAULT 0,
            retry_count     INTEGER NOT NULL DEFAULT 0,
            started_at      TIMESTAMPTZ,
            completed_at    TIMESTAMPTZ,
            error_message   TEXT,
            metadata_extra  JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_embedding_jobs_document_id ON embedding_jobs(document_id);")
    op.execute("CREATE INDEX idx_embedding_jobs_status ON embedding_jobs(status);")
    op.execute(
        "CREATE INDEX idx_embedding_jobs_document_created"
        " ON embedding_jobs(document_id, created_at);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS embedding_jobs CASCADE;")
