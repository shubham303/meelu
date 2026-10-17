"""keyword cluster brand flag

Revision ID: 0626c4a88e31
Revises: 6d2fe0dbe3b5
Create Date: 2026-10-17 19:45:54.542527

"""
from alembic import op
import sqlalchemy as sa


revision = '0626c4a88e31'
down_revision = '6d2fe0dbe3b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('seo_keyword_clusters', sa.Column('is_brand_keyword', sa.Boolean(), nullable=True))
    op.alter_column('seo_keyword_clusters', 'intent', type_=sa.Text(), existing_nullable=True)
    op.alter_column('seo_keyword_clusters', 'importance', type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column('seo_keyword_clusters', 'importance', type_=sa.String(), existing_nullable=True)
    op.alter_column('seo_keyword_clusters', 'intent', type_=sa.String(), existing_nullable=True)
    op.drop_column('seo_keyword_clusters', 'is_brand_keyword')
