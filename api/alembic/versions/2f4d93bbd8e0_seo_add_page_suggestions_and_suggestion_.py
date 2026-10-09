"""seo add page suggestions and suggestion purge index

Revision ID: 2f4d93bbd8e0
Revises: 3bf748a267c4
Create Date: 2026-10-01 13:07:05.478227

"""
from alembic import op
import sqlalchemy as sa


revision = '2f4d93bbd8e0'
down_revision = '3bf748a267c4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_add_page_suggestions',
    sa.Column('core_keyword_id', sa.Text(), nullable=False),
    sa.Column('page_slug', sa.Text(), nullable=False),
    sa.Column('topic', sa.Text(), nullable=False),
    sa.Column('intent', sa.Text(), nullable=True),
    sa.Column('llm_suggestion', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['core_keyword_id'], ['site_keywords.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_add_page_suggestions_created_idx', 'seo_add_page_suggestions', ['created_at'], unique=False)
    op.create_index('seo_add_page_suggestions_keyword_idx', 'seo_add_page_suggestions', ['core_keyword_id'], unique=False)
    op.create_index('seo_add_page_suggestions_status_idx', 'seo_add_page_suggestions', ['site_id', 'status'], unique=False)
    op.create_index('seo_edit_page_suggestions_created_idx', 'seo_edit_page_suggestions', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_edit_page_suggestions_created_idx', table_name='seo_edit_page_suggestions')
    op.drop_index('seo_add_page_suggestions_status_idx', table_name='seo_add_page_suggestions')
    op.drop_index('seo_add_page_suggestions_keyword_idx', table_name='seo_add_page_suggestions')
    op.drop_index('seo_add_page_suggestions_created_idx', table_name='seo_add_page_suggestions')
    op.drop_table('seo_add_page_suggestions')
