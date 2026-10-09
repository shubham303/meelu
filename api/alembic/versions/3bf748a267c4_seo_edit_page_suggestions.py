"""seo edit page suggestions

Revision ID: 3bf748a267c4
Revises: 28d723376de6
Create Date: 2026-10-01 12:57:45.260914

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '3bf748a267c4'
down_revision = '28d723376de6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_edit_page_suggestions',
    sa.Column('page_id', sa.Text(), nullable=False),
    sa.Column('core_keyword_id', sa.Text(), nullable=False),
    sa.Column('strategy', sa.Text(), nullable=False),
    sa.Column('reach_analysis_score', sa.REAL(), nullable=True),
    sa.Column('reach_analysis_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('llm_review', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['core_keyword_id'], ['site_keywords.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['page_id'], ['site_pages.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_edit_page_suggestions_keyword_idx', 'seo_edit_page_suggestions', ['core_keyword_id'], unique=False)
    op.create_index('seo_edit_page_suggestions_page_idx', 'seo_edit_page_suggestions', ['page_id'], unique=False)
    op.create_index('seo_edit_page_suggestions_status_idx', 'seo_edit_page_suggestions', ['site_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_edit_page_suggestions_status_idx', table_name='seo_edit_page_suggestions')
    op.drop_index('seo_edit_page_suggestions_page_idx', table_name='seo_edit_page_suggestions')
    op.drop_index('seo_edit_page_suggestions_keyword_idx', table_name='seo_edit_page_suggestions')
    op.drop_table('seo_edit_page_suggestions')
