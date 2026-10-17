"""gsc country, drop seo rank history

Revision ID: 0eb21b917cce
Revises: 73e72aa5bbcc
Create Date: 2026-10-16 05:40:15.788368

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0eb21b917cce'
down_revision = '73e72aa5bbcc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('seo_rank_history_keyword_idx'), table_name='seo_rank_history')
    op.drop_table('seo_rank_history')
    op.execute('DELETE FROM site_search_daily')
    op.add_column('site_search_daily', sa.Column('country', sa.Text(), nullable=False))
    op.drop_index(op.f('site_search_daily_key_idx'), table_name='site_search_daily')
    op.create_index('site_search_daily_key_idx', 'site_search_daily', ['site_id', 'day', 'query', 'page', 'device', 'country'], unique=True)


def downgrade() -> None:
    op.drop_index('site_search_daily_key_idx', table_name='site_search_daily')
    op.execute('DELETE FROM site_search_daily')
    op.create_index(op.f('site_search_daily_key_idx'), 'site_search_daily', ['site_id', 'day', 'query', 'page', 'device'], unique=True)
    op.drop_column('site_search_daily', 'country')
    op.create_table('seo_rank_history',
    sa.Column('keyword', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('location_code', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('language_code', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('observed_on', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('source', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('url', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('is_site', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('rank_group', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('rank_absolute', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('title', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_rank_history_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_rank_history_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_rank_history_pkey')),
    sa.UniqueConstraint('site_id', 'keyword', 'location_code', 'language_code', 'observed_on', 'url', name=op.f('seo_rank_history_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_rank_history_keyword_idx'), 'seo_rank_history', ['site_id', 'keyword', 'observed_on'], unique=False)
