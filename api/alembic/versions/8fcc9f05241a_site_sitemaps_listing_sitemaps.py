"""site sitemaps listing sitemaps

Revision ID: 8fcc9f05241a
Revises: c0dc0f2c45d9
Create Date: 2026-10-24 14:42:28.966052

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '8fcc9f05241a'
down_revision = 'c0dc0f2c45d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site', sa.Column('sitemaps_listing_sitemaps', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), nullable=False))


def downgrade() -> None:
    op.drop_column('site', 'sitemaps_listing_sitemaps')
