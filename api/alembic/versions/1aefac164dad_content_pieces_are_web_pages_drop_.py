"""content pieces are web pages, drop channels

Revision ID: 1aefac164dad
Revises: 0ae5b070949e
Create Date: 2026-09-27 13:36:13.194252

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '1aefac164dad'
down_revision = '0ae5b070949e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM content_piece_issues WHERE tool = 'channel_rules'")
    op.drop_index(op.f('site_channels_site_channel_idx'), table_name='site_channels')
    op.drop_table('site_channels')
    op.add_column('content_pieces', sa.Column('h1', sa.Text(), server_default=sa.text("''"), nullable=False))
    op.add_column('content_pieces', sa.Column('meta_description', sa.Text(), server_default=sa.text("''"), nullable=False))
    op.add_column('content_pieces', sa.Column('slug', sa.Text(), nullable=True))
    op.add_column('content_pieces', sa.Column('target_keyword', sa.Text(), nullable=True))
    op.drop_index(op.f('content_pieces_parent_idx'), table_name='content_pieces')
    op.drop_index(op.f('content_pieces_site_status_idx'), table_name='content_pieces')
    op.create_index('content_pieces_site_updated_idx', 'content_pieces', ['site_id', 'updated_at'], unique=False)
    op.drop_constraint(op.f('content_pieces_parent_piece_id_fkey'), 'content_pieces', type_='foreignkey')
    op.drop_column('content_pieces', 'status')
    op.drop_column('content_pieces', 'channel_key')
    op.drop_column('content_pieces', 'parent_piece_id')


def downgrade() -> None:
    op.add_column('content_pieces', sa.Column('parent_piece_id', sa.TEXT(), autoincrement=False, nullable=True))
    op.add_column('content_pieces', sa.Column('channel_key', sa.TEXT(), server_default=sa.text("'website'::text"), autoincrement=False, nullable=False))
    op.add_column('content_pieces', sa.Column('status', sa.TEXT(), server_default=sa.text("'draft'::text"), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('content_pieces_parent_piece_id_fkey'), 'content_pieces', 'content_pieces', ['parent_piece_id'], ['id'], ondelete='SET NULL')
    op.drop_index('content_pieces_site_updated_idx', table_name='content_pieces')
    op.create_index(op.f('content_pieces_site_status_idx'), 'content_pieces', ['site_id', 'status'], unique=False)
    op.create_index(op.f('content_pieces_parent_idx'), 'content_pieces', ['parent_piece_id'], unique=False)
    op.drop_column('content_pieces', 'target_keyword')
    op.drop_column('content_pieces', 'slug')
    op.drop_column('content_pieces', 'meta_description')
    op.drop_column('content_pieces', 'h1')
    op.create_table('site_channels',
    sa.Column('channel_key', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('enabled', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.Column('rules', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), autoincrement=False, nullable=False),
    sa.Column('id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('seq', sa.BIGINT(), sa.Identity(always=False, start=1, increment=1, minvalue=1, maxvalue=9223372036854775807, cycle=False, cache=1), autoincrement=True, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), autoincrement=False, nullable=False),
    sa.Column('site_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], name=op.f('site_channels_site_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('site_channels_user_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('site_channels_pkey'))
    )
    op.create_index(op.f('site_channels_site_channel_idx'), 'site_channels', ['site_id', 'channel_key'], unique=True)
