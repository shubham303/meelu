"""site_page has_google_analytics

Revision ID: db5faa718fd4
Revises: cc40cadf2460
Create Date: 2026-09-20 10:33:04.104206

"""
from alembic import op
import sqlalchemy as sa


revision = 'db5faa718fd4'
down_revision = 'cc40cadf2460'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_pages', sa.Column('has_google_analytics', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('site_pages', 'has_google_analytics')
