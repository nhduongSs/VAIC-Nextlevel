"""create bank_products table

Revision ID: 005
Revises: 004
Create Date: 2026-07-19

"""

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE bank_products (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            bank              TEXT NOT NULL,
            product_category  TEXT NOT NULL CHECK (product_category IN ('lai_suat_tien_gui')),
            term              TEXT NOT NULL,
            term_months       NUMERIC,
            customer_segment  TEXT NOT NULL DEFAULT 'ca_nhan'
                                  CHECK (customer_segment IN ('ca_nhan', 'doanh_nghiep')),
            currency          TEXT NOT NULL DEFAULT 'VND',
            rate_value        NUMERIC(6, 3) NOT NULL,
            effective_date    DATE,
            source_url        TEXT,
            content           TEXT NOT NULL,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE (bank, product_category, term, customer_segment, currency)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_bank_products_lookup"
        " ON bank_products (product_category, term, customer_segment);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bank_products CASCADE;")
