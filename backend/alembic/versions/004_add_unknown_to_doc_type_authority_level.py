"""add UNKNOWN to doc_type and authority_level constraints

Revision ID: 004
Revises: 003
Create Date: 2026-07-18

"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE documents DROP CONSTRAINT ck_documents_doc_type;")
    op.execute(
        """
        ALTER TABLE documents ADD CONSTRAINT ck_documents_doc_type CHECK (
            doc_type IN (
                'LAW', 'CIRCULAR', 'DECREE', 'DECISION',
                'POLICY', 'SOP', 'FAQ', 'PRODUCT_DOC', 'MANUAL', 'UNKNOWN'
            )
        );
        """
    )
    op.execute("ALTER TABLE documents DROP CONSTRAINT ck_documents_authority_level;")
    op.execute(
        """
        ALTER TABLE documents ADD CONSTRAINT ck_documents_authority_level CHECK (
            authority_level IN (
                'NATIONAL_LAW', 'NHNN_CIRCULAR', 'NHNN_DECISION',
                'INTERNAL_POLICY', 'DEPARTMENT_SOP', 'FAQ', 'UNKNOWN'
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE documents DROP CONSTRAINT ck_documents_doc_type;")
    op.execute(
        """
        ALTER TABLE documents ADD CONSTRAINT ck_documents_doc_type CHECK (
            doc_type IN (
                'LAW', 'CIRCULAR', 'DECREE', 'DECISION',
                'POLICY', 'SOP', 'FAQ', 'PRODUCT_DOC', 'MANUAL'
            )
        );
        """
    )
    op.execute("ALTER TABLE documents DROP CONSTRAINT ck_documents_authority_level;")
    op.execute(
        """
        ALTER TABLE documents ADD CONSTRAINT ck_documents_authority_level CHECK (
            authority_level IN (
                'NATIONAL_LAW', 'NHNN_CIRCULAR', 'NHNN_DECISION',
                'INTERNAL_POLICY', 'DEPARTMENT_SOP', 'FAQ'
            )
        );
        """
    )
