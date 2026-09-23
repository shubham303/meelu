"""drop social publishing

Revision ID: 2869f586a1e4
Revises: af9a67713b10
Create Date: 2026-09-19 12:34:22.420547

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2869f586a1e4'
down_revision = 'af9a67713b10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE content_pieces SET status = 'draft' "
        "WHERE status IN ('scheduled', 'posted', 'failed')"
    )
    op.drop_index(op.f('social_accounts_provider_idx'), table_name='social_accounts')
    op.drop_index(op.f('social_accounts_site_idx'), table_name='social_accounts')
    op.drop_table('social_accounts')
    op.drop_index(op.f('content_pieces_slot_idx'), table_name='content_pieces')
    op.drop_column('content_pieces', 'posted_at')
    op.drop_column('content_pieces', 'posted_url')
    op.drop_column('content_pieces', 'failure')
    op.drop_column('content_pieces', 'scheduled_at')
    op.drop_column('content_pieces', 'external_post_id')
    op.drop_column('site_channels', 'timezone')
    op.drop_column('site_channels', 'min_gap_hours')
    op.drop_column('site_channels', 'posting_windows')


def downgrade() -> None:
    op.add_column('site_channels', sa.Column('posting_windows', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), autoincrement=False, nullable=False))
    op.add_column('site_channels', sa.Column('min_gap_hours', sa.INTEGER(), server_default=sa.text('24'), autoincrement=False, nullable=False))
    op.add_column('site_channels', sa.Column('timezone', sa.TEXT(), server_default=sa.text("'UTC'::text"), autoincrement=False, nullable=False))
    op.add_column('content_pieces', sa.Column('external_post_id', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('content_pieces', sa.Column('scheduled_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.add_column('content_pieces', sa.Column('failure', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('content_pieces', sa.Column('posted_url', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('content_pieces', sa.Column('posted_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True))
    op.create_index(op.f('content_pieces_slot_idx'), 'content_pieces', ['site_id', 'channel_key', 'scheduled_at'], unique=False)
    op.create_table('social_accounts',
    sa.Column('provider', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('external_account_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('social_accounts_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('social_accounts_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('social_accounts_pkey'))
    )
    op.create_index(op.f('social_accounts_site_idx'), 'social_accounts', ['site_id'], unique=True)
    op.create_index(op.f('social_accounts_provider_idx'), 'social_accounts', ['provider', 'external_account_id'], unique=False)
