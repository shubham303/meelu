"""site keywords

Revision ID: 8870e7081e9a
Revises: dbdfa4fede7e
Create Date: 2026-09-30 13:43:43.697177

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '8870e7081e9a'
down_revision = 'dbdfa4fede7e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('site_keywords',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('keyword_key', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('is_rejected', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('seeds', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('monthly_searches', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('cpc', sa.REAL(), nullable=True),
    sa.Column('ads_competition', sa.REAL(), nullable=True),
    sa.Column('ads_competition_level', sa.Text(), nullable=True),
    sa.Column('keyword_difficulty', sa.Integer(), nullable=True),
    sa.Column('core_keyword', sa.Text(), nullable=True),
    sa.Column('main_intent', sa.Text(), nullable=True),
    sa.Column('foreign_intents', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('top10_rank', sa.REAL(), nullable=True),
    sa.Column('top10_main_domain_rank', sa.REAL(), nullable=True),
    sa.Column('top10_referring_domains', sa.REAL(), nullable=True),
    sa.Column('metrics_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'keyword_key', name='site_keywords_key')
    )
    op.create_index('site_keywords_volume_idx', 'site_keywords', ['site_id', 'is_rejected', 'search_volume'], unique=False)


def downgrade() -> None:
    op.drop_index('site_keywords_volume_idx', table_name='site_keywords')
    op.drop_table('site_keywords')
