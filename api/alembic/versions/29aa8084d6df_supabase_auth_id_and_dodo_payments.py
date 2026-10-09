"""supabase auth id and dodo payments

Revision ID: 29aa8084d6df
Revises: f7e8807acb2d
Create Date: 2026-10-08 15:05:13.360469

"""
from alembic import op
import sqlalchemy as sa


revision = '29aa8084d6df'
down_revision = 'f7e8807acb2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('payment',
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('credit_micros', sa.BigInteger(), nullable=False),
    sa.Column('checkout_session_id', sa.Text(), nullable=True),
    sa.Column('checkout_url', sa.Text(), nullable=True),
    sa.Column('dodo_payment_id', sa.Text(), nullable=True),
    sa.Column('paid_amount', sa.Integer(), nullable=True),
    sa.Column('paid_currency', sa.Text(), nullable=True),
    sa.Column('credited_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('checkout_session_id'),
    sa.UniqueConstraint('dodo_payment_id')
    )
    op.create_index('payment_user_idx', 'payment', ['user_id', 'seq'], unique=False)
    op.add_column('user', sa.Column('auth_id', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_user_auth_id'), 'user', ['auth_id'], unique=True)
    op.drop_column('user', 'hashed_password')


def downgrade() -> None:
    op.add_column('user', sa.Column('hashed_password', sa.VARCHAR(length=1024), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_user_auth_id'), table_name='user')
    op.drop_column('user', 'auth_id')
    op.drop_index('payment_user_idx', table_name='payment')
    op.drop_table('payment')
