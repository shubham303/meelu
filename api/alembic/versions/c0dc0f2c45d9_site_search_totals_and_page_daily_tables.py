"""site search totals and page daily tables

Revision ID: c0dc0f2c45d9
Revises: 19670b1ebee2
Create Date: 2026-10-23 12:39:24.055998

"""
from alembic import op
import sqlalchemy as sa


revision = 'c0dc0f2c45d9'
down_revision = '19670b1ebee2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('site_search_page_daily',
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('page', sa.Text(), nullable=False),
    sa.Column('clicks', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('impressions', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('position', sa.REAL(), nullable=False),
    sa.Column('final', sa.Boolean(), server_default=sa.text('true'), nullable=False),
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
    op.create_index('site_search_page_daily_key_idx', 'site_search_page_daily', ['site_id', 'day', 'page'], unique=True)
    op.create_index('site_search_page_daily_page_idx', 'site_search_page_daily', ['site_id', 'page', 'day'], unique=False)
    op.create_table('site_search_totals_daily',
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('device', sa.Text(), nullable=False),
    sa.Column('clicks', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('impressions', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('position', sa.REAL(), nullable=False),
    sa.Column('final', sa.Boolean(), server_default=sa.text('true'), nullable=False),
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
    op.create_index('site_search_totals_daily_key_idx', 'site_search_totals_daily', ['site_id', 'day', 'device'], unique=True)


def downgrade() -> None:
    op.drop_index('site_search_totals_daily_key_idx', table_name='site_search_totals_daily')
    op.drop_table('site_search_totals_daily')
    op.drop_index('site_search_page_daily_page_idx', table_name='site_search_page_daily')
    op.drop_index('site_search_page_daily_key_idx', table_name='site_search_page_daily')
    op.drop_table('site_search_page_daily')
