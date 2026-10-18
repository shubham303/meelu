"""find leads desk and shared social search cursor

Revision ID: dd6464a04866
Revises: 45f2950c6b02
Create Date: 2026-10-18 17:43:57.343073

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'dd6464a04866'
down_revision = '45f2950c6b02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('social_search_cursor',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('platform', sa.Text(), nullable=False),
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('last_fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('platform', 'keyword', name='social_search_cursor_platform_keyword_key')
    )
    op.create_table('lead_brief',
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('source', sa.Text(), server_default=sa.text("'user'"), nullable=False),
    sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('plan', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'text', name='lead_brief_site_text_key')
    )
    op.create_index('lead_brief_site_idx', 'lead_brief', ['site_id', 'seq'], unique=False)
    op.create_table('lead_run',
    sa.Column('status', sa.Text(), server_default=sa.text("'running'"), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('found_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('shortlisted_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('kept_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('source_stats', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('error', sa.Text(), nullable=True),
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
    op.create_index('lead_run_one_running_per_user', 'lead_run', ['user_id'], unique=True, postgresql_where=sa.text("status = 'running'"))
    op.create_index('lead_run_site_idx', 'lead_run', ['site_id', 'seq'], unique=False)
    op.create_table('lead_seen',
    sa.Column('identity_key', sa.Text(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'identity_key', name='lead_seen_site_identity_key')
    )
    op.create_index('lead_seen_kind_seen_idx', 'lead_seen', ['kind', 'seen_at'], unique=False)
    op.create_table('lead',
    sa.Column('brief_id', sa.Text(), nullable=True),
    sa.Column('run_id', sa.Text(), nullable=True),
    sa.Column('identity_key', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('platform', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('handle', sa.Text(), nullable=True),
    sa.Column('headline', sa.Text(), nullable=True),
    sa.Column('profile_url', sa.Text(), nullable=True),
    sa.Column('email', sa.Text(), nullable=True),
    sa.Column('email_source_url', sa.Text(), nullable=True),
    sa.Column('website', sa.Text(), nullable=True),
    sa.Column('snippet', sa.Text(), nullable=True),
    sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('activity', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('enriched_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reason', sa.Text(), nullable=True),
    sa.Column('angle', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'candidate'"), nullable=False),
    sa.Column('contacted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('discarded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['brief_id'], ['lead_brief.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['run_id'], ['lead_run.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'identity_key', name='lead_site_identity_key')
    )
    op.create_index('lead_run_idx', 'lead', ['run_id'], unique=False)
    op.create_index('lead_site_status_idx', 'lead', ['site_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_index('lead_site_status_idx', table_name='lead')
    op.drop_index('lead_run_idx', table_name='lead')
    op.drop_table('lead')
    op.drop_index('lead_seen_kind_seen_idx', table_name='lead_seen')
    op.drop_table('lead_seen')
    op.drop_index('lead_run_site_idx', table_name='lead_run')
    op.drop_index('lead_run_one_running_per_user', table_name='lead_run', postgresql_where=sa.text("status = 'running'"))
    op.drop_table('lead_run')
    op.drop_index('lead_brief_site_idx', table_name='lead_brief')
    op.drop_table('lead_brief')
    op.drop_table('social_search_cursor')
