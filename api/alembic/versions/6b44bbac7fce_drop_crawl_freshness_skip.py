"""drop crawl freshness skip

Revision ID: 6b44bbac7fce
Revises: 099e6f7ecf80
Create Date: 2026-10-13 12:11:18.936330

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '6b44bbac7fce'
down_revision = '099e6f7ecf80'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('site_crawl_jobs', 'skipped')
    op.drop_column('site_crawl_jobs', 'cutoff_days')
    op.drop_column('site_crawl_jobs', 'fresh_before')


def downgrade() -> None:
    op.add_column('site_crawl_jobs', sa.Column('fresh_before', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('site_crawl_jobs', sa.Column('cutoff_days', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('site_crawl_jobs', sa.Column('skipped', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False))
