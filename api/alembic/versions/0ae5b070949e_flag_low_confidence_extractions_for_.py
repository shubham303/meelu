"""flag low confidence extractions for large llm review

Revision ID: 0ae5b070949e
Revises: c0939d54e616
Create Date: 2026-09-27 13:22:12.998840

"""
from alembic import op
import sqlalchemy as sa


revision = '0ae5b070949e'
down_revision = 'c0939d54e616'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_page_llm_extraction', sa.Column('use_large_llm_review', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index('site_page_llm_extraction_review_idx', 'site_page_llm_extraction', ['site_id'], unique=False, postgresql_where=sa.text('use_large_llm_review'))
    op.execute(
        "UPDATE site_page_llm_extraction SET use_large_llm_review = true "
        "WHERE error IS NULL AND ("
        "(page_type IS NULL AND confidence IS NOT NULL) OR "
        "(broad_page_type IS NULL AND broad_page_type_confidence IS NOT NULL))"
    )


def downgrade() -> None:
    op.drop_index('site_page_llm_extraction_review_idx', table_name='site_page_llm_extraction', postgresql_where=sa.text('use_large_llm_review'))
    op.drop_column('site_page_llm_extraction', 'use_large_llm_review')
