"""seo reach queries and targets

Revision ID: 215b81ec4d5c
Revises: 476d827158bd
Create Date: 2026-09-29 21:37:18.399825

"""
from alembic import op
import sqlalchemy as sa


revision = '215b81ec4d5c'
down_revision = '476d827158bd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_reach_queries',
    sa.Column('job_id', sa.Text(), nullable=False),
    sa.Column('query', sa.Text(), nullable=False),
    sa.Column('page_url', sa.Text(), nullable=False),
    sa.Column('device', sa.Text(), nullable=False),
    sa.Column('serp_device', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('impressions', sa.Integer(), nullable=False),
    sa.Column('clicks', sa.Integer(), nullable=False),
    sa.Column('gsc_position', sa.REAL(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('position_source', sa.Text(), nullable=False),
    sa.Column('page_rank', sa.REAL(), nullable=True),
    sa.Column('domain_rank', sa.REAL(), nullable=True),
    sa.Column('strength', sa.REAL(), nullable=False),
    sa.Column('likely_position', sa.Integer(), nullable=False),
    sa.Column('expected_position', sa.REAL(), nullable=False),
    sa.Column('p_page_one', sa.REAL(), nullable=True),
    sa.Column('p_top_three', sa.REAL(), nullable=True),
    sa.Column('target_count', sa.Integer(), nullable=False),
    sa.Column('serp_fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['job_id'], ['seo_jobs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_reach_queries_job_idx', 'seo_reach_queries', ['site_id', 'job_id'], unique=False)
    op.create_index('seo_reach_queries_page_idx', 'seo_reach_queries', ['site_id', 'page_url'], unique=False)
    op.create_table('seo_reach_targets',
    sa.Column('reach_query_id', sa.Text(), nullable=False),
    sa.Column('rank_group', sa.Integer(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('page_rank', sa.REAL(), nullable=True),
    sa.Column('domain_rank', sa.REAL(), nullable=True),
    sa.Column('strength', sa.REAL(), nullable=False),
    sa.Column('smoothed_strength', sa.REAL(), nullable=False),
    sa.Column('pass_chance', sa.REAL(), nullable=False),
    sa.Column('reach', sa.REAL(), nullable=False),
    sa.Column('is_target', sa.Boolean(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['reach_query_id'], ['seo_reach_queries.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_reach_targets_query_idx', 'seo_reach_targets', ['reach_query_id', 'rank_group'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_reach_targets_query_idx', table_name='seo_reach_targets')
    op.drop_table('seo_reach_targets')
    op.drop_index('seo_reach_queries_page_idx', table_name='seo_reach_queries')
    op.drop_index('seo_reach_queries_job_idx', table_name='seo_reach_queries')
    op.drop_table('seo_reach_queries')
