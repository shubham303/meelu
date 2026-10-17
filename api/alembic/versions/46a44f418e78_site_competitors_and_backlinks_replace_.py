"""site competitors and backlinks replace seo lists

Revision ID: 46a44f418e78
Revises: 0626c4a88e31
Create Date: 2026-10-17 20:27:19.417203

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '46a44f418e78'
down_revision = '0626c4a88e31'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('site_backlinks',
    sa.Column('site_domain', sa.Text(), nullable=False),
    sa.Column('backlink_url', sa.Text(), nullable=False),
    sa.Column('backlinking_domain', sa.Text(), nullable=False),
    sa.Column('backlinking_url', sa.Text(), nullable=False),
    sa.Column('anchor', sa.Text(), nullable=True),
    sa.Column('item_type', sa.Text(), nullable=True),
    sa.Column('dofollow', sa.Boolean(), nullable=True),
    sa.Column('link_attributes', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('semantic_location', sa.Text(), nullable=True),
    sa.Column('links_from_domain', sa.Integer(), nullable=True),
    sa.Column('is_lost', sa.Boolean(), nullable=True),
    sa.Column('is_broken', sa.Boolean(), nullable=True),
    sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
    sa.Column('backlink_spam_score', sa.Integer(), nullable=True),
    sa.Column('domain_spam_score', sa.Integer(), nullable=True),
    sa.Column('domain_rank', sa.Integer(), nullable=True),
    sa.Column('page_rank', sa.Integer(), nullable=True),
    sa.Column('is_ip', sa.Boolean(), nullable=True),
    sa.Column('platform_type', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('country', sa.Text(), nullable=True),
    sa.Column('page_title', sa.Text(), nullable=True),
    sa.Column('page_language', sa.Text(), nullable=True),
    sa.Column('page_status_code', sa.Integer(), nullable=True),
    sa.Column('page_external_links', sa.Integer(), nullable=True),
    sa.Column('is_genuine', sa.Boolean(), nullable=False),
    sa.Column('dismissed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'site_domain', 'backlinking_url', 'backlink_url', name='site_backlinks_key')
    )
    op.create_index('site_backlinks_genuine_idx', 'site_backlinks', ['site_id', 'is_genuine', 'backlinking_domain'], unique=False)
    op.create_index('site_backlinks_target_idx', 'site_backlinks', ['site_id', 'site_domain'], unique=False)
    op.create_table('site_competitors',
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('domain_rank', sa.Integer(), nullable=True),
    sa.Column('backlinks_fetched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'domain', name='site_competitors_key')
    )
    op.create_index('site_competitors_site_idx', 'site_competitors', ['site_id', 'created_at'], unique=False)
    op.execute(
        "INSERT INTO site_competitors (id, user_id, site_id, domain, created_at, updated_at) "
        "SELECT id, user_id, site_id, domain, created_at, updated_at FROM seo_competitors ORDER BY seq"
    )
    op.drop_index(op.f('seo_competitors_site_idx'), table_name='seo_competitors')
    op.drop_table('seo_competitors')
    op.drop_table('site_seo')


def downgrade() -> None:
    op.create_table('site_seo',
    sa.Column('backlink_opportunities', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('site_seo_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('site_seo_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('site_seo_pkey')),
    sa.UniqueConstraint('site_id', name=op.f('site_seo_site_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_table('seo_competitors',
    sa.Column('domain', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('seo_competitors_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('seo_competitors_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('seo_competitors_pkey')),
    sa.UniqueConstraint('site_id', 'domain', name=op.f('seo_competitors_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('seo_competitors_site_idx'), 'seo_competitors', ['site_id', 'created_at'], unique=False)
    op.drop_index('site_competitors_site_idx', table_name='site_competitors')
    op.drop_table('site_competitors')
    op.drop_index('site_backlinks_target_idx', table_name='site_backlinks')
    op.drop_index('site_backlinks_genuine_idx', table_name='site_backlinks')
    op.drop_table('site_backlinks')
