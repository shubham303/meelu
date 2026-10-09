"""site keywords drop is_rejected

Revision ID: 28d723376de6
Revises: 8870e7081e9a
Create Date: 2026-10-01 11:39:40.857379

"""
from alembic import op
import sqlalchemy as sa


revision = '28d723376de6'
down_revision = '8870e7081e9a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('site_keywords_volume_idx'), table_name='site_keywords')
    op.create_index('site_keywords_volume_idx', 'site_keywords', ['site_id', 'search_volume'], unique=False)
    op.drop_column('site_keywords', 'is_rejected')


def downgrade() -> None:
    op.add_column('site_keywords', sa.Column('is_rejected', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.drop_index('site_keywords_volume_idx', table_name='site_keywords')
    op.create_index(op.f('site_keywords_volume_idx'), 'site_keywords', ['site_id', 'is_rejected', 'search_volume'], unique=False)
