"""bill websites per domain

Revision ID: 249753b9321f
Revises: 3214f8dbcad0
Create Date: 2026-09-23 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '249753b9321f'
down_revision = '3214f8dbcad0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_billing', sa.Column('domain', sa.Text(), nullable=True))
    op.execute(
        "UPDATE site_billing b SET domain = s.domain FROM site s WHERE s.id = b.site_id"
    )
    op.execute("DELETE FROM site_billing WHERE domain IS NULL")
    op.alter_column('site_billing', 'domain', nullable=False)

    op.drop_constraint('site_billing_pkey', 'site_billing', type_='primary')
    op.create_primary_key('site_billing_pkey', 'site_billing', ['user_id', 'domain'])

    op.alter_column('site_billing', 'site_id', existing_type=sa.Text(), nullable=True)
    op.drop_constraint('site_billing_site_id_fkey', 'site_billing', type_='foreignkey')
    op.create_foreign_key(
        'site_billing_site_id_fkey', 'site_billing', 'site', ['site_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('site_billing_site_idx', 'site_billing', ['site_id'], unique=False)


def downgrade() -> None:
    op.drop_index('site_billing_site_idx', table_name='site_billing')
    op.drop_constraint('site_billing_site_id_fkey', 'site_billing', type_='foreignkey')
    op.execute("DELETE FROM site_billing WHERE site_id IS NULL")
    op.alter_column('site_billing', 'site_id', existing_type=sa.Text(), nullable=False)
    op.create_foreign_key(
        'site_billing_site_id_fkey', 'site_billing', 'site', ['site_id'], ['id'],
        ondelete='CASCADE',
    )
    op.drop_constraint('site_billing_pkey', 'site_billing', type_='primary')
    op.create_primary_key('site_billing_pkey', 'site_billing', ['site_id'])
    op.drop_column('site_billing', 'domain')
