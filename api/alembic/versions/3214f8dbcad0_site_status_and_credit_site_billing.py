"""site status and credit site billing

Revision ID: 3214f8dbcad0
Revises: 17929a8cafaa
Create Date: 2026-09-23 10:51:49.959196

"""
from alembic import op
import sqlalchemy as sa


revision = '3214f8dbcad0'
down_revision = '17929a8cafaa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('site_billing',
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('last_charged_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('charge_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('charged_micros', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('site_id')
    )
    op.create_index('site_billing_due_idx', 'site_billing', ['last_charged_at'], unique=False)
    op.add_column('site', sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False))
    op.execute(
        "INSERT INTO site_billing (site_id, user_id) "
        "SELECT id, user_id FROM site ON CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_column('site', 'status')
    op.drop_index('site_billing_due_idx', table_name='site_billing')
    op.drop_table('site_billing')
