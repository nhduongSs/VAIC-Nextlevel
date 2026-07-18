"""create chunks, document_relations, processing_logs tables

Revision ID: 002
Revises: 001
Create Date: 2026-07-18

"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── chunks ────────────────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE chunks (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            content         TEXT NOT NULL,
            chunk_index     INTEGER NOT NULL,
            page_number     INTEGER,
            section_title   VARCHAR(300),
            section_number  VARCHAR(50),
            chunk_type      VARCHAR(30) NOT NULL DEFAULT 'PARAGRAPH',
            token_count     BIGINT,
            embedding       VECTOR(1024),
            search_vector   TSVECTOR,
            metadata_extra  JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_chunks_chunk_type CHECK (
                chunk_type IN ('ARTICLE','CLAUSE','PARAGRAPH','TABLE','DEFINITION','APPENDIX')
            )
        );
        """
    )

    op.execute("CREATE INDEX idx_chunks_document_id ON chunks(document_id);")
    op.execute("CREATE INDEX idx_chunks_document_index ON chunks(document_id, chunk_index);")
    op.execute("CREATE INDEX idx_chunks_search_vector ON chunks USING GIN(search_vector);")
    # HNSW index requires pgvector — created only when embeddings are populated (Wave 2.3)
    op.execute(
        """
        CREATE INDEX idx_chunks_embedding_hnsw ON chunks
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """
    )

    # Auto-update search_vector trigger for chunks
    op.execute(
        """
        CREATE OR REPLACE FUNCTION chunks_search_vector_update()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('simple', coalesce(NEW.content, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_chunks_search_vector
            BEFORE INSERT OR UPDATE ON chunks
            FOR EACH ROW EXECUTE FUNCTION chunks_search_vector_update();
        """
    )

    # ── document_relations ────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE document_relations (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            source_doc_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            target_doc_id   UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            relation_type   VARCHAR(50) NOT NULL,
            description     TEXT,
            confidence      FLOAT NOT NULL DEFAULT 1.0,
            metadata_extra  JSONB NOT NULL DEFAULT '{}',
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_document_relations_type CHECK (
                relation_type IN (
                    'REPLACES','AMENDS','REFERENCES',
                    'SUPPLEMENTS','IMPLEMENTS','CONFLICTS_WITH'
                )
            ),
            CONSTRAINT ck_document_relations_confidence CHECK (confidence BETWEEN 0 AND 1),
            CONSTRAINT ck_document_relations_no_self CHECK (source_doc_id != target_doc_id)
        );
        """
    )

    op.execute("CREATE INDEX idx_relations_source ON document_relations(source_doc_id);")
    op.execute("CREATE INDEX idx_relations_target ON document_relations(target_doc_id);")
    op.execute("CREATE INDEX idx_relations_type ON document_relations(relation_type);")

    # ── processing_logs ───────────────────────────────────────────────────────
    op.execute(
        """
        CREATE TABLE processing_logs (
            id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            status          VARCHAR(30) NOT NULL,
            current_stage   VARCHAR(50),
            started_at      TIMESTAMP WITH TIME ZONE NOT NULL,
            completed_at    TIMESTAMP WITH TIME ZONE,
            error_message   TEXT,
            stage_results   JSONB NOT NULL DEFAULT '{}',
            retry_count     INTEGER NOT NULL DEFAULT 0,
            created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),

            CONSTRAINT ck_processing_logs_status CHECK (
                status IN (
                    'QUEUED','PARSING','EXTRACTING_METADATA','CLASSIFYING',
                    'EXTRACTING_RELATIONSHIPS','CHUNKING','COMPLETED','FAILED'
                )
            )
        );
        """
    )

    op.execute("CREATE INDEX idx_processing_logs_document_id ON processing_logs(document_id);")
    op.execute("CREATE INDEX idx_processing_logs_status ON processing_logs(status);")
    op.execute("CREATE INDEX idx_processing_logs_created_at ON processing_logs(created_at DESC);")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_chunks_search_vector ON chunks;")
    op.execute("DROP FUNCTION IF EXISTS chunks_search_vector_update;")
    op.execute("DROP TABLE IF EXISTS processing_logs;")
    op.execute("DROP TABLE IF EXISTS document_relations;")
    op.execute("DROP TABLE IF EXISTS chunks;")
