"""create documents table

Revision ID: 001
Revises:
Create Date: 2026-07-18

"""

from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.execute(
        """
        CREATE TABLE documents (
            id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            title            VARCHAR(500) NOT NULL,
            doc_number       VARCHAR(100),
            doc_type         VARCHAR(50)  NOT NULL,
            authority_level  VARCHAR(50)  NOT NULL,
            issued_date      DATE,
            effective_date   DATE,
            expired_date     DATE,
            status           VARCHAR(30)  NOT NULL DEFAULT 'UPLOADED',
            issuing_body     VARCHAR(200),
            filename         VARCHAR(500) NOT NULL,
            original_filename VARCHAR(500) NOT NULL,
            content_type     VARCHAR(100) NOT NULL,
            file_size        BIGINT       NOT NULL,
            file_path        VARCHAR(500) NOT NULL,
            content_hash     VARCHAR(64)  NOT NULL UNIQUE,
            version          INTEGER      NOT NULL DEFAULT 1,
            tags             JSONB        NOT NULL DEFAULT '[]',
            metadata_extra   JSONB        NOT NULL DEFAULT '{}',
            search_vector    TSVECTOR,
            created_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            deleted_at       TIMESTAMP WITH TIME ZONE,

            CONSTRAINT ck_documents_status CHECK (
                status IN ('UPLOADED', 'PROCESSING', 'READY', 'FAILED', 'ARCHIVED')
            ),
            CONSTRAINT ck_documents_doc_type CHECK (
                doc_type IN (
                    'LAW', 'CIRCULAR', 'DECREE', 'DECISION',
                    'POLICY', 'SOP', 'FAQ', 'PRODUCT_DOC', 'MANUAL'
                )
            ),
            CONSTRAINT ck_documents_authority_level CHECK (
                authority_level IN (
                    'NATIONAL_LAW', 'NHNN_CIRCULAR', 'NHNN_DECISION',
                    'INTERNAL_POLICY', 'DEPARTMENT_SOP', 'FAQ'
                )
            )
        );
        """
    )

    # Partial indexes on non-deleted rows
    op.execute(
        "CREATE INDEX idx_documents_doc_type ON documents(doc_type) WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX idx_documents_authority_level ON documents(authority_level) "
        "WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX idx_documents_issued_date ON documents(issued_date DESC) "
        "WHERE deleted_at IS NULL;"
    )
    op.execute("CREATE INDEX idx_documents_status ON documents(status) WHERE deleted_at IS NULL;")
    op.execute(
        "CREATE INDEX idx_documents_doc_number ON documents(doc_number) WHERE deleted_at IS NULL;"
    )

    # Standard indexes
    op.execute("CREATE INDEX idx_documents_content_hash ON documents(content_hash);")
    op.execute("CREATE INDEX idx_documents_search_vector ON documents USING GIN(search_vector);")
    op.execute("CREATE INDEX idx_documents_tags ON documents USING GIN(tags);")
    op.execute("CREATE INDEX idx_documents_created_at ON documents(created_at DESC);")

    # Auto-update search_vector trigger
    op.execute(
        """
        CREATE OR REPLACE FUNCTION documents_search_vector_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('simple',
                coalesce(NEW.title, '') || ' ' ||
                coalesce(NEW.doc_number, '') || ' ' ||
                coalesce(NEW.issuing_body, '')
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_documents_search_vector
            BEFORE INSERT OR UPDATE ON documents
            FOR EACH ROW EXECUTE FUNCTION documents_search_vector_update();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_documents_search_vector ON documents;")
    op.execute("DROP FUNCTION IF EXISTS documents_search_vector_update;")
    op.execute("DROP TABLE IF EXISTS documents;")
