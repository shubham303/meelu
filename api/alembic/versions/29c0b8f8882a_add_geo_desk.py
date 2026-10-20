"""add geo desk

Revision ID: 29c0b8f8882a
Revises: d32601bfeccd
Create Date: 2026-10-20 10:25:29.058874

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '29c0b8f8882a'
down_revision = 'd32601bfeccd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('geo_query',
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('source', sa.Text(), server_default=sa.text("'user'"), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'text', name='geo_query_site_text_key')
    )
    op.create_index('geo_query_site_idx', 'geo_query', ['site_id', 'seq'], unique=False)
    op.create_table('geo_check',
    sa.Column('query_id', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'running'"), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('intent', sa.Text(), nullable=True),
    sa.Column('required_points', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('verdict', sa.Text(), nullable=True),
    sa.Column('page_id', sa.Text(), nullable=True),
    sa.Column('page_url', sa.Text(), nullable=True),
    sa.Column('position', sa.REAL(), nullable=True),
    sa.Column('pages', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('ai_answers', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('page_adds', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('suggestion', sa.Text(), nullable=True),
    sa.Column('model', sa.Text(), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['page_id'], ['site_pages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['query_id'], ['geo_query.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('geo_check_one_running_per_query', 'geo_check', ['query_id'], unique=True, postgresql_where=sa.text("status = 'running'"))
    op.create_index('geo_check_query_idx', 'geo_check', ['query_id', 'seq'], unique=False)
    op.create_index('geo_check_site_idx', 'geo_check', ['site_id', 'seq'], unique=False)


def downgrade() -> None:
    op.drop_index('geo_check_site_idx', table_name='geo_check')
    op.drop_index('geo_check_query_idx', table_name='geo_check')
    op.drop_index('geo_check_one_running_per_query', table_name='geo_check', postgresql_where=sa.text("status = 'running'"))
    op.drop_table('geo_check')
    op.drop_index('geo_query_site_idx', table_name='geo_query')
    op.drop_table('geo_query')
