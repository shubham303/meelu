"""social accounts

Revision ID: 61fa53e5d78a
Revises: 8d044bc0812f
Create Date: 2026-09-12 21:21:56.249810

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '61fa53e5d78a'
down_revision = '8d044bc0812f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('social_accounts',
    sa.Column('provider', sa.Text(), nullable=False),
    sa.Column('external_account_id', sa.Text(), nullable=False),
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
    op.create_index('social_accounts_provider_idx', 'social_accounts', ['provider', 'external_account_id'], unique=False)
    op.create_index('social_accounts_site_idx', 'social_accounts', ['site_id'], unique=True)
    op.drop_index(op.f('social_publishing_group_idx'), table_name='social_publishing')
    op.drop_index(op.f('social_publishing_site_idx'), table_name='social_publishing')
    op.drop_table('social_publishing')


def downgrade() -> None:
    op.create_table('social_publishing',
    sa.Column('profile_group_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('posts_this_month', sa.INTEGER(), server_default=sa.text('0'), autoincrement=False, nullable=False),
    sa.Column('month_key', sa.TEXT(), server_default=sa.text("''::text"), autoincrement=False, nullable=False),
    sa.Column('last_post_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=True),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('social_publishing_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('social_publishing_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('social_publishing_pkey'))
    )
    op.create_index(op.f('social_publishing_site_idx'), 'social_publishing', ['site_id'], unique=True)
    op.create_index(op.f('social_publishing_group_idx'), 'social_publishing', ['profile_group_id'], unique=True)
    op.drop_index('social_accounts_site_idx', table_name='social_accounts')
    op.drop_index('social_accounts_provider_idx', table_name='social_accounts')
    op.drop_table('social_accounts')
