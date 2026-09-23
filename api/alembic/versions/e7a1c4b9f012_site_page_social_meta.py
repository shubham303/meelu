"""site_page social_meta

Revision ID: e7a1c4b9f012
Revises: db5faa718fd4
Create Date: 2026-09-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'e7a1c4b9f012'
down_revision = 'db5faa718fd4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'site_pages',
        sa.Column(
            'social_meta',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column('site_pages', 'social_meta')
