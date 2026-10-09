"""seo rank and volume history

Revision ID: f164a2b0e67b
Revises: 6a4d76f7e51a
Create Date: 2026-10-06 19:41:04.526093

"""
from alembic import op
import sqlalchemy as sa


revision = 'f164a2b0e67b'
down_revision = '6a4d76f7e51a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_rank_history',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('observed_on', sa.Date(), nullable=False),
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('is_site', sa.Boolean(), nullable=False),
    sa.Column('rank_group', sa.Integer(), nullable=False),
    sa.Column('rank_absolute', sa.Integer(), nullable=True),
    sa.Column('title', sa.Text(), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'keyword', 'location_code', 'language_code', 'observed_on', 'url', name='seo_rank_history_key')
    )
    op.create_index('seo_rank_history_keyword_idx', 'seo_rank_history', ['site_id', 'keyword', 'observed_on'], unique=False)
    op.create_table('seo_volume_history',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('month', sa.Date(), nullable=False),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('clickstream_volume', sa.Integer(), nullable=True),
    sa.Column('cpc', sa.REAL(), nullable=True),
    sa.Column('competition', sa.REAL(), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'keyword', 'location_code', 'language_code', 'month', name='seo_volume_history_key')
    )
    op.create_index('seo_volume_history_keyword_idx', 'seo_volume_history', ['site_id', 'keyword', 'month'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_volume_history_keyword_idx', table_name='seo_volume_history')
    op.drop_table('seo_volume_history')
    op.drop_index('seo_rank_history_keyword_idx', table_name='seo_rank_history')
    op.drop_table('seo_rank_history')
