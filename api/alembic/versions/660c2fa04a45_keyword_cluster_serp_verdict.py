"""keyword cluster serp verdict

Revision ID: 660c2fa04a45
Revises: 0eb21b917cce
Create Date: 2026-10-16 19:15:30.748157

"""
from alembic import op
import sqlalchemy as sa


revision = '660c2fa04a45'
down_revision = '0eb21b917cce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seo_keyword_clusters", sa.Column("serp_verdict", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("seo_keyword_clusters", "serp_verdict")
