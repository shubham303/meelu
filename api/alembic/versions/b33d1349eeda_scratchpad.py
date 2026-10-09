"""scratchpad

Revision ID: b33d1349eeda
Revises: 2684c684b47d
Create Date: 2026-10-03 12:59:02.295663

"""
from alembic import op
import sqlalchemy as sa


revision = 'b33d1349eeda'
down_revision = '2684c684b47d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('scratchpad',
    sa.Column('tool_name', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('scratchpad_updated_idx', 'scratchpad', ['updated_at'], unique=False)
    op.create_index('scratchpad_user_idx', 'scratchpad', ['user_id'], unique=False)
    op.create_table('scratchpad_row',
    sa.Column('scratchpad_id', sa.Text(), nullable=False),
    sa.Column('row_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('text_hash', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('status_updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('attempt_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('priority', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('result', sa.Text(), nullable=True),
    sa.Column('error_reason', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['scratchpad_id'], ['scratchpad.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('scratchpad_id', 'row_id'),
    sa.UniqueConstraint('scratchpad_id', 'text_hash', name='scratchpad_row_hash_key')
    )
    op.create_index('scratchpad_row_claim_idx', 'scratchpad_row', ['scratchpad_id', 'status', sa.literal_column('priority DESC'), sa.literal_column('row_id ASC')], unique=False)
    op.create_index('scratchpad_row_status_age_idx', 'scratchpad_row', ['status', 'status_updated_at'], unique=False)


def downgrade() -> None:
    op.drop_index('scratchpad_row_status_age_idx', table_name='scratchpad_row')
    op.drop_index('scratchpad_row_claim_idx', table_name='scratchpad_row')
    op.drop_table('scratchpad_row')
    op.drop_index('scratchpad_user_idx', table_name='scratchpad')
    op.drop_index('scratchpad_updated_idx', table_name='scratchpad')
    op.drop_table('scratchpad')
