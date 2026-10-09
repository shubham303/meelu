"""drop seo desk tables

Revision ID: 0f8dd065ea2f
Revises: 49349aa17d1f
Create Date: 2026-10-06 19:13:19.547031

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0f8dd065ea2f'
down_revision = '49349aa17d1f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('seo_edit_page_suggestions_created_idx'), table_name='seo_edit_page_suggestions')
    op.drop_index(op.f('seo_edit_page_suggestions_keyword_idx'), table_name='seo_edit_page_suggestions')
    op.drop_index(op.f('seo_edit_page_suggestions_page_idx'), table_name='seo_edit_page_suggestions')
    op.drop_index(op.f('seo_edit_page_suggestions_status_idx'), table_name='seo_edit_page_suggestions')
    op.drop_table('seo_edit_page_suggestions')
    op.drop_index(op.f('seo_serps_expires_idx'), table_name='seo_serps')
    op.drop_table('seo_serps')
    op.drop_index(op.f('seo_add_page_suggestions_created_idx'), table_name='seo_add_page_suggestions')
    op.drop_index(op.f('seo_add_page_suggestions_keyword_idx'), table_name='seo_add_page_suggestions')
    op.drop_index(op.f('seo_add_page_suggestions_status_idx'), table_name='seo_add_page_suggestions')
    op.drop_table('seo_add_page_suggestions')
    op.drop_table('seo_keyword_months')
    op.drop_index(op.f('site_keywords_created_idx'), table_name='site_keywords')
    op.drop_table('site_keywords')
    op.drop_index(op.f('seo_keywords_cluster_idx'), table_name='seo_keywords')
    op.drop_index(op.f('seo_keywords_overview_fetched_idx'), table_name='seo_keywords')
    op.drop_table('seo_keywords')
    op.drop_index(op.f('seo_domains_expires_idx'), table_name='seo_domains')
    op.drop_table('seo_domains')
    op.drop_index(op.f('seo_pages_domain_idx'), table_name='seo_pages')
    op.drop_index(op.f('seo_pages_expires_idx'), table_name='seo_pages')
    op.drop_table('seo_pages')
    op.drop_index(op.f('seo_jobs_site_idx'), table_name='seo_jobs')
    op.drop_table('seo_jobs')


def downgrade() -> None:
    op.create_table('seo_jobs',
    sa.Column('prompt', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'RUNNING'::text"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_jobs_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_jobs_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_jobs_pkey'))
    )
    op.create_index(op.f('seo_jobs_site_idx'), 'seo_jobs', ['site_id', 'status'], unique=False)
    op.create_table('seo_pages',
    sa.Column('url', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('rank', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('rank_data', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('rank_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('rank_expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('title', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('meta_description', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('h1', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('headings', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('word_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('schema_types', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('published_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('modified_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('content_hash', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('content_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('content_expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('main_domain_rank', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('referring_main_domains', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('referring_main_domains_nofollow', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('spam_score', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('first_seen', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('url', name=op.f('seo_pages_pkey'))
    )
    op.create_index(op.f('seo_pages_expires_idx'), 'seo_pages', ['expires_at'], unique=False)
    op.create_index(op.f('seo_pages_domain_idx'), 'seo_pages', ['domain'], unique=False)
    op.create_table('seo_domains',
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('location_code', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('language_code', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('rank', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('organic_etv', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('organic_keywords', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('paid_etv', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('paid_keywords', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('referring_main_domains', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('referring_main_domains_nofollow', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('spam_score', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('first_seen', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('domain', 'location_code', 'language_code', name=op.f('seo_domains_pkey'))
    )
    op.create_index(op.f('seo_domains_expires_idx'), 'seo_domains', ['expires_at'], unique=False)
    op.create_table('seo_keywords',
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('keyword', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('location_code', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('words_count', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('cpc', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('ads_competition', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('ads_competition_level', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('low_top_of_page_bid', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('high_top_of_page_bid', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('categories', postgresql.ARRAY(sa.INTEGER()), server_default=sa.text("'{}'::integer[]"), autoincrement=False, nullable=False),
    sa.Column('clickstream_search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('gender_female', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('gender_male', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('age_18_24', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('age_25_34', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('age_35_44', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('age_45_54', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('age_55_64', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('keyword_difficulty', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('core_keyword', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('synonym_algorithm', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('main_intent', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('foreign_intents', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('cluster_center', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('top10_backlinks', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_dofollow', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_referring_pages', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_referring_domains', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_referring_main_domains', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_rank', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('top10_main_domain_rank', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('serp_item_types', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('serp_results_count', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('ai_search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('overview_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('clickstream_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('history_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('ai_fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('vendor_updated_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_keywords_pkey')),
    sa.UniqueConstraint('keyword', 'location_code', name=op.f('seo_keywords_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_keywords_overview_fetched_idx'), 'seo_keywords', ['overview_fetched_at'], unique=False)
    op.create_index(op.f('seo_keywords_cluster_idx'), 'seo_keywords', ['location_code', 'cluster_center'], unique=False)
    op.create_table('site_keywords',
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seeds', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('is_site_ranked', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('site_keywords_keyword_id_fkey'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('site_keywords_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('site_keywords_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('site_keywords_pkey')),
    sa.UniqueConstraint('site_id', 'keyword_id', name=op.f('site_keywords_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('site_keywords_created_idx'), 'site_keywords', ['site_id', 'created_at'], unique=False)
    op.create_table('seo_keyword_months',
    sa.Column('keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('month', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('clickstream_search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('ai_search_volume', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('cpc', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('ads_competition', sa.REAL(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], name=op.f('seo_keyword_months_keyword_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('keyword_id', 'month', name=op.f('seo_keyword_months_pkey'))
    )
    op.create_table('seo_add_page_suggestions',
    sa.Column('core_keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('page_slug', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('topic', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('intent', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('llm_suggestion', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'draft'::text"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['core_keyword_id'], ['site_keywords.id'], name=op.f('seo_add_page_suggestions_core_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_add_page_suggestions_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_add_page_suggestions_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_add_page_suggestions_pkey'))
    )
    op.create_index(op.f('seo_add_page_suggestions_status_idx'), 'seo_add_page_suggestions', ['site_id', 'status'], unique=False)
    op.create_index(op.f('seo_add_page_suggestions_keyword_idx'), 'seo_add_page_suggestions', ['core_keyword_id'], unique=False)
    op.create_index(op.f('seo_add_page_suggestions_created_idx'), 'seo_add_page_suggestions', ['created_at'], unique=False)
    op.create_table('seo_serps',
    sa.Column('keyword', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('location_code', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('language_code', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('device', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('source', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('depth', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('check_url', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('results_count', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('item_types', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('questions', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('related_searches', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('ai_overview_citations', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('fetched_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('captured_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('keyword', 'location_code', 'language_code', 'device', 'source', name=op.f('seo_serps_pkey'))
    )
    op.create_index(op.f('seo_serps_expires_idx'), 'seo_serps', ['expires_at'], unique=False)
    op.create_table('seo_edit_page_suggestions',
    sa.Column('page_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('core_keyword_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('strategy', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('reach_analysis_score', sa.REAL(), autoincrement=False, nullable=True),
    sa.Column('reach_analysis_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('llm_review', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('status', sa.TEXT(), server_default=sa.text("'draft'::text"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['core_keyword_id'], ['site_keywords.id'], name=op.f('seo_edit_page_suggestions_core_keyword_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['page_id'], ['site_pages.id'], name=op.f('seo_edit_page_suggestions_page_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_edit_page_suggestions_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_edit_page_suggestions_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_edit_page_suggestions_pkey'))
    )
    op.create_index(op.f('seo_edit_page_suggestions_status_idx'), 'seo_edit_page_suggestions', ['site_id', 'status'], unique=False)
    op.create_index(op.f('seo_edit_page_suggestions_page_idx'), 'seo_edit_page_suggestions', ['page_id'], unique=False)
    op.create_index(op.f('seo_edit_page_suggestions_keyword_idx'), 'seo_edit_page_suggestions', ['core_keyword_id'], unique=False)
    op.create_index(op.f('seo_edit_page_suggestions_created_idx'), 'seo_edit_page_suggestions', ['created_at'], unique=False)
