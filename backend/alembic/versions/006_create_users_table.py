"""create users table with seeded admin/staff accounts

Revision ID: 006
Revises: 005
Create Date: 2026-07-19

"""

import json

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

# Seed passwords (demo/dev only — rotate before any real deployment):
#   admin@gmail.com  / Admin@123
#   lananh.nguyen@gmail.com / NhanVien@123
#   vanhung.tran@gmail.com  / NhanVien@123
ADMIN_PASSWORD_HASH = "$2b$12$h9gVn88SWr9LUw3zVqqfXOSrD8tYx7X1ZBbJ/rqDOEenH4bFLYDG6"
STAFF_PASSWORD_HASH = "$2b$12$rZ407bxZLqsQYgSIde9Zfu1WMgsbzikubrOvYOcKwzOCvX.mJ8.Ae"

ADMIN_PERMISSIONS = [
    "users:manage",
    "documents:upload",
    "documents:manage",
    "documents:delete",
    "chat:use",
    "dashboard:view",
]
STAFF_PERMISSIONS = [
    "documents:upload",
    "chat:use",
    "dashboard:view",
]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE users (
            id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email             VARCHAR(255) NOT NULL UNIQUE,
            hashed_password   VARCHAR(255) NOT NULL,
            full_name         VARCHAR(200) NOT NULL,
            role              VARCHAR(20) NOT NULL DEFAULT 'STAFF'
                                  CHECK (role IN ('ADMIN', 'STAFF')),
            permissions       JSONB NOT NULL DEFAULT '[]'::jsonb,
            is_active         BOOLEAN NOT NULL DEFAULT TRUE,
            created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_users_role ON users (role);")

    admin_perms = json.dumps(ADMIN_PERMISSIONS)
    staff_perms = json.dumps(STAFF_PERMISSIONS)

    op.execute(
        f"""
        INSERT INTO users (email, hashed_password, full_name, role, permissions, is_active)
        VALUES
            (
                'admin@gmail.com',
                '{ADMIN_PASSWORD_HASH}',
                'Phạm Minh Đức',
                'ADMIN',
                '{admin_perms}'::jsonb,
                TRUE
            ),
            (
                'lananh.nguyen@gmail.com',
                '{STAFF_PASSWORD_HASH}',
                'Nguyễn Thị Lan Anh',
                'STAFF',
                '{staff_perms}'::jsonb,
                TRUE
            ),
            (
                'vanhung.tran@gmail.com',
                '{STAFF_PASSWORD_HASH}',
                'Trần Văn Hùng',
                'STAFF',
                '{staff_perms}'::jsonb,
                TRUE
            )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
