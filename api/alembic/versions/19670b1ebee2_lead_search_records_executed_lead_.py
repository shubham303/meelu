"""lead_search records executed lead queries

Revision ID: 19670b1ebee2
Revises: 0c9d6343b4b7
Create Date: 2026-10-23 11:36:04.850422

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '19670b1ebee2'
down_revision = '0c9d6343b4b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('lead_search',
    sa.Column('platform', sa.Text(), nullable=False),
    sa.Column('query', sa.Text(), nullable=False),
    sa.Column('page', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('searched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('results', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'platform', 'query', name='lead_search_site_query_key')
    )
    op.create_index('lead_search_searched_idx', 'lead_search', ['searched_at'], unique=False)


def downgrade() -> None:
    op.drop_index('lead_search_searched_idx', table_name='lead_search')
    op.drop_table('lead_search')
