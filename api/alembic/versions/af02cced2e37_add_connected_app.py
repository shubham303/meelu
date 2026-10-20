"""add connected_app

Revision ID: af02cced2e37
Revises: 556a418ec3d7
Create Date: 2026-10-20 15:22:00.771186

"""
from alembic import op
import sqlalchemy as sa

revision = 'af02cced2e37'
down_revision = '556a418ec3d7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('connected_app',
    sa.Column('site_id', sa.Text(), nullable=True),
    sa.Column('desk', sa.Text(), nullable=False),
    sa.Column('toolkit', sa.Text(), nullable=False),
    sa.Column('account_id', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('label', sa.Text(), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=True),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('account_id')
    )
    op.create_index('connected_app_site_idx', 'connected_app', ['site_id', 'desk', 'toolkit'], unique=False)


def downgrade() -> None:
    op.drop_index('connected_app_site_idx', table_name='connected_app')
    op.drop_table('connected_app')
