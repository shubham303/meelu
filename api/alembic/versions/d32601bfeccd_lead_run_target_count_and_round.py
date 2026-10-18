"""lead run target count and round

Revision ID: d32601bfeccd
Revises: dd6464a04866
Create Date: 2026-10-18 18:27:05.350816

"""
from alembic import op
import sqlalchemy as sa


revision = 'd32601bfeccd'
down_revision = 'dd6464a04866'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('lead_run', sa.Column('target_count', sa.Integer(), server_default=sa.text('20'), nullable=False))
    op.add_column('lead_run', sa.Column('round', sa.Integer(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    op.drop_column('lead_run', 'round')
    op.drop_column('lead_run', 'target_count')
