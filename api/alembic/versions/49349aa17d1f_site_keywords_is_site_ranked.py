"""site_keywords is_site_ranked

Revision ID: 49349aa17d1f
Revises: 6d0124702242
Create Date: 2026-10-06 13:00:53.298139

"""
from alembic import op
import sqlalchemy as sa


revision = '49349aa17d1f'
down_revision = '6d0124702242'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_keywords', sa.Column('is_site_ranked', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('site_keywords', 'is_site_ranked')
