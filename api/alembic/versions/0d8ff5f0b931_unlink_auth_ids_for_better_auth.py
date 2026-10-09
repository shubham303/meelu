"""unlink auth ids for better auth

Revision ID: 0d8ff5f0b931
Revises: c58ea3b3db67
Create Date: 2026-10-10 02:21:08.080090

"""
from alembic import op

revision = '0d8ff5f0b931'
down_revision = 'c58ea3b3db67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('UPDATE "user" SET auth_id = NULL')


def downgrade() -> None:
    pass
