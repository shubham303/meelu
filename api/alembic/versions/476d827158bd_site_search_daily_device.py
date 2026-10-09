"""site search daily device

Revision ID: 476d827158bd
Revises: 1ad13f6dcf3d
Create Date: 2026-09-29 21:05:41.667430

"""
from alembic import op
import sqlalchemy as sa


revision = '476d827158bd'
down_revision = '1ad13f6dcf3d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM site_search_daily")
    op.add_column('site_search_daily', sa.Column('device', sa.Text(), nullable=False))
    op.drop_index(op.f('site_search_daily_key_idx'), table_name='site_search_daily')
    op.create_index('site_search_daily_key_idx', 'site_search_daily', ['site_id', 'day', 'query', 'page', 'device'], unique=True)


def downgrade() -> None:
    op.drop_index('site_search_daily_key_idx', table_name='site_search_daily')
    op.create_index(op.f('site_search_daily_key_idx'), 'site_search_daily', ['site_id', 'day', 'query', 'page'], unique=True)
    op.drop_column('site_search_daily', 'device')
