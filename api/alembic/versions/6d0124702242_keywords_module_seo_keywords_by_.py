"""keywords module: seo_keywords by location, keyword months, site_keywords as pointers

Revision ID: 6d0124702242
Revises: b33d1349eeda
Create Date: 2026-10-05 12:36:37.697970

"""
from alembic import op
import sqlalchemy as sa

revision = '6d0124702242'
down_revision = 'b33d1349eeda'
branch_labels = None
depends_on = None

SUGGESTION_TABLES = ('seo_edit_page_suggestions', 'seo_add_page_suggestions')


def upgrade() -> None:
    for table in SUGGESTION_TABLES:
        op.drop_constraint(f'{table}_core_keyword_id_fkey', table, type_='foreignkey')
    op.drop_table('site_keywords')
    op.drop_table('seo_keywords')
    op.drop_table('seo_clickstream_volumes')

    op.create_table('seo_keywords',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('words_count', sa.Integer(), nullable=True),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('cpc', sa.REAL(), nullable=True),
    sa.Column('ads_competition', sa.REAL(), nullable=True),
    sa.Column('ads_competition_level', sa.Text(), nullable=True),
    sa.Column('low_top_of_page_bid', sa.REAL(), nullable=True),
    sa.Column('high_top_of_page_bid', sa.REAL(), nullable=True),
    sa.Column('categories', sa.ARRAY(sa.Integer()), server_default=sa.text("'{}'::integer[]"), nullable=False),
    sa.Column('clickstream_search_volume', sa.Integer(), nullable=True),
    sa.Column('gender_female', sa.REAL(), nullable=True),
    sa.Column('gender_male', sa.REAL(), nullable=True),
    sa.Column('age_18_24', sa.REAL(), nullable=True),
    sa.Column('age_25_34', sa.REAL(), nullable=True),
    sa.Column('age_35_44', sa.REAL(), nullable=True),
    sa.Column('age_45_54', sa.REAL(), nullable=True),
    sa.Column('age_55_64', sa.REAL(), nullable=True),
    sa.Column('keyword_difficulty', sa.Integer(), nullable=True),
    sa.Column('core_keyword', sa.Text(), nullable=True),
    sa.Column('synonym_algorithm', sa.Text(), nullable=True),
    sa.Column('main_intent', sa.Text(), nullable=True),
    sa.Column('foreign_intents', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('cluster_center', sa.Text(), nullable=True),
    sa.Column('top10_backlinks', sa.REAL(), nullable=True),
    sa.Column('top10_dofollow', sa.REAL(), nullable=True),
    sa.Column('top10_referring_pages', sa.REAL(), nullable=True),
    sa.Column('top10_referring_domains', sa.REAL(), nullable=True),
    sa.Column('top10_referring_main_domains', sa.REAL(), nullable=True),
    sa.Column('top10_rank', sa.REAL(), nullable=True),
    sa.Column('top10_main_domain_rank', sa.REAL(), nullable=True),
    sa.Column('serp_item_types', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('serp_results_count', sa.BigInteger(), nullable=True),
    sa.Column('ai_search_volume', sa.Integer(), nullable=True),
    sa.Column('overview_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('clickstream_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('history_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('ai_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('vendor_updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('keyword', 'location_code', name='seo_keywords_key')
    )
    op.create_index('seo_keywords_cluster_idx', 'seo_keywords', ['location_code', 'cluster_center'], unique=False)
    op.create_index('seo_keywords_overview_fetched_idx', 'seo_keywords', ['overview_fetched_at'], unique=False)

    op.create_table('seo_keyword_months',
    sa.Column('keyword_id', sa.Text(), nullable=False),
    sa.Column('month', sa.Date(), nullable=False),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('clickstream_search_volume', sa.Integer(), nullable=True),
    sa.Column('ai_search_volume', sa.Integer(), nullable=True),
    sa.Column('cpc', sa.REAL(), nullable=True),
    sa.Column('ads_competition', sa.REAL(), nullable=True),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('keyword_id', 'month')
    )

    op.create_table('site_keywords',
    sa.Column('keyword_id', sa.Text(), nullable=False),
    sa.Column('seeds', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['keyword_id'], ['seo_keywords.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'keyword_id', name='site_keywords_key')
    )
    op.create_index('site_keywords_created_idx', 'site_keywords', ['site_id', 'created_at'], unique=False)

    for table in SUGGESTION_TABLES:
        op.create_foreign_key(
            f'{table}_core_keyword_id_fkey', table, 'site_keywords',
            ['core_keyword_id'], ['id'], ondelete='CASCADE',
        )


def downgrade() -> None:
    raise NotImplementedError("Rebuild from an empty database instead.")
