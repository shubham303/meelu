"""seo keyword clusters

Revision ID: 857f3fca42da
Revises: 2b7bcc1b10b8
Create Date: 2026-10-06 20:21:11.267683

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '857f3fca42da'
down_revision = '2b7bcc1b10b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_keyword_clusters',
    sa.Column('main_keyword', sa.Text(), nullable=False),
    sa.Column('keywords', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('core_keyword', sa.Text(), nullable=True),
    sa.Column('seeds', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('volume', sa.Integer(), nullable=False),
    sa.Column('winnability', sa.REAL(), nullable=True),
    sa.Column('p_top_three', sa.REAL(), nullable=True),
    sa.Column('p_page_one', sa.REAL(), nullable=True),
    sa.Column('likely_position', sa.Integer(), nullable=True),
    sa.Column('our_position', sa.Integer(), nullable=True),
    sa.Column('our_url', sa.Text(), nullable=True),
    sa.Column('our_strength', sa.REAL(), nullable=True),
    sa.Column('intent_fit', sa.REAL(), nullable=True),
    sa.Column('competitors', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('metrics_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'location_code', 'language_code', 'main_keyword', name='seo_keyword_clusters_key')
    )
    op.create_index('seo_keyword_clusters_rank_idx', 'seo_keyword_clusters', ['site_id', 'winnability', 'volume'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_keyword_clusters_rank_idx', table_name='seo_keyword_clusters')
    op.drop_table('seo_keyword_clusters')
