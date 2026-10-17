"""keyword cluster intent and importance

Revision ID: 6d2fe0dbe3b5
Revises: c4d58dfec2e8
Create Date: 2026-10-17 19:26:54.743380

"""
from alembic import op
import sqlalchemy as sa


revision = '6d2fe0dbe3b5'
down_revision = 'c4d58dfec2e8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('seo_keyword_clusters', sa.Column('intent', sa.String(), nullable=True))
    op.add_column('seo_keyword_clusters', sa.Column('importance', sa.String(), nullable=True))
    op.create_index('seo_keyword_clusters_importance_idx', 'seo_keyword_clusters', ['site_id', 'importance'], unique=False)
    op.create_index('seo_keyword_clusters_intent_idx', 'seo_keyword_clusters', ['site_id', 'intent'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_keyword_clusters_intent_idx', table_name='seo_keyword_clusters')
    op.drop_index('seo_keyword_clusters_importance_idx', table_name='seo_keyword_clusters')
    op.drop_column('seo_keyword_clusters', 'importance')
    op.drop_column('seo_keyword_clusters', 'intent')
