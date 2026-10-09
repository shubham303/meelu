"""seo rebuild: drop old seo tables, add seo_jobs

Revision ID: 663f995ab8a4
Revises: 1aefac164dad
Create Date: 2026-09-29 12:49:42.415292

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '663f995ab8a4'
down_revision = '1aefac164dad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS "
        + ", ".join(
            [
                'seo_page_suggestion_keywords',
                'seo_page_suggestions',
                'seo_serp_results',
                'seo_serp_snapshots',
                'seo_keyword_content_pages',
                'seo_keyword_gsc_pages',
                'seo_competitor_keywords',
                'seo_competitors',
                'seo_keyword_clusters',
                'seo_keywords',
                'seo_page_facts',
                'seo_site_state',
                'seo_jobs',
            ]
        )
        + " CASCADE"
    )
    op.create_table('seo_jobs',
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'RUNNING'"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_jobs_site_idx', 'seo_jobs', ['site_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_jobs_site_idx', table_name='seo_jobs')
    op.drop_table('seo_jobs')
    op.create_table('seo_jobs',
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'RUNNING'"), nullable=False),
    sa.Column('vendor_calls', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('vendor_micros', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('vendor_ceiling_micros', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('seo_jobs_site_idx', 'seo_jobs', ['site_id', 'status'], unique=False)
    op.create_table('seo_page_suggestion_keywords',
    sa.Column('suggestion_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_page_suggestion_keywords_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['suggestion_id'], ['seo_page_suggestions.id'], name=op.f('seo_page_suggestion_keywords_suggestion_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('suggestion_id', 'keyword_id', name=op.f('seo_page_suggestion_keywords_pkey'))
    )
    op.create_table('seo_page_facts',
    sa.Column('page_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('url', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('status', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('redirect_to', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('page_type', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('lang', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('title', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('h1', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('headings', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('meta_description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('title_pixels', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('word_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('inlinks', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('link_score', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('published_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('first_seen_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('content_hash', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('indexable', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('live', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('is_home', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('impressions_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('clicks_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('impressions_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('clicks_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_page_facts_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_page_facts_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_page_facts_pkey'))
    )
    op.create_index(op.f('seo_page_facts_site_idx'), 'seo_page_facts', ['site_id', 'live'], unique=False)
    op.create_index(op.f('seo_page_facts_page_idx'), 'seo_page_facts', ['page_id'], unique=True)
    op.create_table('seo_keyword_clusters',
    sa.Column('head_keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('centroid', pgvector.sqlalchemy.vector.VECTOR(dim=384), autoincrement=False, nullable=True),
    sa.Column('size', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('volume_sum', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('difficulty_median', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('owner_page_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('owner_coverage', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('site_similarity', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('rebuilt_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['head_keyword_id'], ['seo_keywords.id'], name=op.f('seo_keyword_clusters_head_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_keyword_clusters_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_keyword_clusters_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_keyword_clusters_pkey'))
    )
    op.create_index(op.f('seo_keyword_clusters_site_idx'), 'seo_keyword_clusters', ['site_id'], unique=False)
    op.create_table('seo_serp_results',
    sa.Column('snapshot_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('rank', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('url', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('title', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('is_ours', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_serp_results_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['snapshot_id'], ['seo_serp_snapshots.id'], name=op.f('seo_serp_results_snapshot_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_serp_results_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_serp_results_pkey'))
    )
    op.create_index(op.f('seo_serp_results_snapshot_idx'), 'seo_serp_results', ['snapshot_id', 'rank'], unique=False)
    op.create_table('seo_competitor_keywords',
    sa.Column('competitor_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('position', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('url', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('etv', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['competitor_id'], ['seo_competitors.id'], name=op.f('seo_competitor_keywords_competitor_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_competitor_keywords_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_competitor_keywords_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_competitor_keywords_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_competitor_keywords_pkey')),
    sa.UniqueConstraint('competitor_id', 'keyword_id', name=op.f('seo_competitor_keywords_pair_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_competitor_keywords_keyword_idx'), 'seo_competitor_keywords', ['keyword_id'], unique=False)
    op.create_table('seo_serp_snapshots',
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('device', sa.TEXT(), server_default=sa.text("'desktop'::text"), autoincrement=False, nullable=False),
    sa.Column('fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('features', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_serp_snapshots_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_serp_snapshots_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_serp_snapshots_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_serp_snapshots_pkey'))
    )
    op.create_index(op.f('seo_serp_snapshots_keyword_idx'), 'seo_serp_snapshots', ['site_id', 'keyword_id', 'device', 'fetched_at'], unique=False)
    op.create_table('seo_keyword_gsc_pages',
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('page_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('position', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('impressions_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('clicks_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('impressions_prev_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('clicks_prev_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('impressions_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('clicks_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('ctr', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('ctr_gap', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('leader_days_90d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('coverage', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('lexical_hit', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('computed_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_keyword_gsc_pages_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_keyword_gsc_pages_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_keyword_gsc_pages_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_keyword_gsc_pages_pkey')),
    sa.UniqueConstraint('keyword_id', 'page_id', name=op.f('seo_keyword_gsc_pages_pair_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_keyword_gsc_pages_page_idx'), 'seo_keyword_gsc_pages', ['site_id', 'page_id'], unique=False)
    op.create_index(op.f('seo_keyword_gsc_pages_keyword_idx'), 'seo_keyword_gsc_pages', ['site_id', 'keyword_id'], unique=False)
    op.create_table('seo_competitors',
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('brand_terms', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('first_source', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('intersections', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('avg_position', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('state', sa.TEXT(), server_default=sa.text("'candidate'::text"), autoincrement=False, nullable=False),
    sa.Column('fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_competitors_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_competitors_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_competitors_pkey')),
    sa.UniqueConstraint('site_id', 'domain', name=op.f('seo_competitors_site_domain_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_competitors_state_idx'), 'seo_competitors', ['site_id', 'state'], unique=False)
    op.create_table('seo_page_suggestions',
    sa.Column('job_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('action', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('page_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('topic_key', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('cluster_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('pair_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('merge_into_page_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('strategies', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('suggestion', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('coverage_at_creation', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('impressions_at_creation', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('target_position', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('state', sa.TEXT(), server_default=sa.text("'draft'::text"), autoincrement=False, nullable=False),
    sa.Column('search_score', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('confidence', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('score', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('verified_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['cluster_id'], ['seo_keyword_clusters.id'], name=op.f('seo_page_suggestions_cluster_id_fkey'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['job_id'], ['seo_jobs.id'], name=op.f('seo_page_suggestions_job_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pair_id'], ['seo_page_suggestions.id'], name=op.f('seo_page_suggestions_pair_id_fkey'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_page_suggestions_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_page_suggestions_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_page_suggestions_pkey'))
    )
    op.create_index(op.f('seo_page_suggestions_state_idx'), 'seo_page_suggestions', ['site_id', 'state'], unique=False)
    op.create_index(op.f('seo_page_suggestions_pair_idx'), 'seo_page_suggestions', ['pair_id'], unique=False)
    op.create_index(op.f('seo_page_suggestions_page_key'), 'seo_page_suggestions', ['site_id', 'action', 'page_id', 'topic_key'], unique=True, postgresql_where='(page_id IS NOT NULL)')
    op.create_index(op.f('seo_page_suggestions_job_idx'), 'seo_page_suggestions', ['job_id'], unique=False)
    op.create_index(op.f('seo_page_suggestions_add_key'), 'seo_page_suggestions', ['site_id', 'action', 'topic_key'], unique=True, postgresql_where='(page_id IS NULL)')
    op.create_table('seo_keywords',
    sa.Column('keyword', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('difficulty', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('cpc', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('intent', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('facts_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('first_source', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seed_keyword_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('cluster_id', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('branded', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('our_position', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('our_url', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=384), autoincrement=False, nullable=True),
    sa.Column('embed_model', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('embed_error', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('impressions_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('clicks_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('impressions_prev_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('clicks_prev_28d', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('impressions_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('clicks_ly_28d', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['cluster_id'], ['seo_keyword_clusters.id'], name=op.f('seo_keywords_cluster_id_fkey'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['seed_keyword_id'], ['seo_keywords.id'], name=op.f('seo_keywords_seed_keyword_id_fkey'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_keywords_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_keywords_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_keywords_pkey')),
    sa.UniqueConstraint('site_id', 'keyword', name=op.f('seo_keywords_site_keyword_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_keywords_pending_idx'), 'seo_keywords', ['site_id'], unique=False, postgresql_where='(embedding IS NULL)')
    op.create_index(op.f('seo_keywords_embedding_idx'), 'seo_keywords', ['embedding'], unique=False, postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_using='hnsw')
    op.create_index(op.f('seo_keywords_cluster_idx'), 'seo_keywords', ['site_id', 'cluster_id'], unique=False)
    op.create_index(op.f('seo_keywords_branded_idx'), 'seo_keywords', ['site_id', 'branded'], unique=False)
    op.create_table('seo_keyword_content_pages',
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('page_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('coverage', sa.REAL(), autoincrement=False, nullable=False),
    sa.Column('lexical_hit', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False),
    sa.Column('computed_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_keyword_content_pages_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_keyword_content_pages_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_keyword_content_pages_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_keyword_content_pages_pkey')),
    sa.UniqueConstraint('keyword_id', 'page_id', name=op.f('seo_keyword_content_pages_pair_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_keyword_content_pages_page_idx'), 'seo_keyword_content_pages', ['site_id', 'page_id'], unique=False)
    op.create_index(op.f('seo_keyword_content_pages_keyword_idx'), 'seo_keyword_content_pages', ['site_id', 'keyword_id'], unique=False)
    op.create_table('seo_site_state',
    sa.Column('location_code', sa.INTEGER(), server_default=sa.text('2840'), autoincrement=False, nullable=False),
    sa.Column('language_code', sa.TEXT(), server_default=sa.text("'en'::text"), autoincrement=False, nullable=False),
    sa.Column('brand_terms', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('precompute_requested_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('rollup_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('embedded_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('ctr_curve', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_site_state_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_site_state_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_site_state_pkey'))
    )
    op.create_index(op.f('seo_site_state_site_idx'), 'seo_site_state', ['site_id'], unique=True)
