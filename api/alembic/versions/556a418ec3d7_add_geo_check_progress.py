"""add geo check progress

Revision ID: 556a418ec3d7
Revises: 29c0b8f8882a
Create Date: 2026-10-20 11:15:51.032273

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '556a418ec3d7'
down_revision = '29c0b8f8882a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('geo_check', sa.Column('progress', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))


def downgrade() -> None:
    op.drop_column('geo_check', 'progress')
