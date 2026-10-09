"""seo keywords table

Revision ID: 9dae09298633
Revises: 663f995ab8a4
Create Date: 2026-09-29 14:05:30.750693

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '9dae09298633'
down_revision = '663f995ab8a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_keywords',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('monthly_searches', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('cpc', sa.REAL(), nullable=True),
    sa.Column('ads_competition', sa.REAL(), nullable=True),
    sa.Column('ads_competition_level', sa.Text(), nullable=True),
    sa.Column('keyword_difficulty', sa.Integer(), nullable=True),
    sa.Column('core_keyword', sa.Text(), nullable=True),
    sa.Column('synonym_algorithm', sa.Text(), nullable=True),
    sa.Column('main_intent', sa.Text(), nullable=True),
    sa.Column('foreign_intents', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('top10_rank', sa.REAL(), nullable=True),
    sa.Column('top10_main_domain_rank', sa.REAL(), nullable=True),
    sa.Column('top10_referring_domains', sa.REAL(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('keyword', 'location_code', 'language_code')
    )
    op.create_index('seo_keywords_core_idx', 'seo_keywords', ['location_code', 'language_code', 'core_keyword'], unique=False)
    op.create_index('seo_keywords_expires_idx', 'seo_keywords', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_keywords_expires_idx', table_name='seo_keywords')
    op.drop_index('seo_keywords_core_idx', table_name='seo_keywords')
    op.drop_table('seo_keywords')
