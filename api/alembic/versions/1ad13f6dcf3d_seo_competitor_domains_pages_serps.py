"""seo competitor domains pages serps

Revision ID: 1ad13f6dcf3d
Revises: 9dae09298633
Create Date: 2026-09-29 14:33:01.269853

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1ad13f6dcf3d'
down_revision = '9dae09298633'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_domains',
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('organic_etv', sa.REAL(), nullable=True),
    sa.Column('organic_keywords', sa.Integer(), nullable=True),
    sa.Column('paid_etv', sa.REAL(), nullable=True),
    sa.Column('paid_keywords', sa.Integer(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('domain', 'location_code', 'language_code')
    )
    op.create_index('seo_domains_expires_idx', 'seo_domains', ['expires_at'], unique=False)
    op.create_table('seo_pages',
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('rank_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('rank_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('rank_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('meta_description', sa.Text(), nullable=True),
    sa.Column('h1', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('headings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('word_count', sa.Integer(), nullable=True),
    sa.Column('schema_types', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('modified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('content_hash', sa.Text(), nullable=True),
    sa.Column('content_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('content_expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('url')
    )
    op.create_index('seo_pages_domain_idx', 'seo_pages', ['domain'], unique=False)
    op.create_index('seo_pages_expires_idx', 'seo_pages', ['expires_at'], unique=False)
    op.create_table('seo_serps',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('device', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('depth', sa.Integer(), nullable=False),
    sa.Column('check_url', sa.Text(), nullable=True),
    sa.Column('results_count', sa.BigInteger(), nullable=True),
    sa.Column('item_types', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('questions', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('related_searches', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('ai_overview_citations', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('keyword', 'location_code', 'language_code', 'device', 'source')
    )
    op.create_index('seo_serps_expires_idx', 'seo_serps', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_serps_expires_idx', table_name='seo_serps')
    op.drop_table('seo_serps')
    op.drop_index('seo_pages_expires_idx', table_name='seo_pages')
    op.drop_index('seo_pages_domain_idx', table_name='seo_pages')
    op.drop_table('seo_pages')
    op.drop_index('seo_domains_expires_idx', table_name='seo_domains')
    op.drop_table('seo_domains')
