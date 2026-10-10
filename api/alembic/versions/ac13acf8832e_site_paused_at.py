"""site paused_at

Revision ID: ac13acf8832e
Revises: 0d8ff5f0b931
Create Date: 2026-10-10 11:50:35.678866

"""
from alembic import op
import sqlalchemy as sa


revision = 'ac13acf8832e'
down_revision = '0d8ff5f0b931'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site', sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True))
    op.execute("UPDATE site SET paused_at = updated_at WHERE status = 'disabled'")


def downgrade() -> None:
    op.drop_column('site', 'paused_at')
