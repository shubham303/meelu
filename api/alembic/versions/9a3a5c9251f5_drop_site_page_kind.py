"""drop site page kind

Revision ID: 9a3a5c9251f5
Revises: 249753b9321f
Create Date: 2026-09-23 14:30:30.108957

"""
import sqlalchemy as sa
from alembic import op

revision = '9a3a5c9251f5'
down_revision = '249753b9321f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('seo_page_facts', 'kind')
    op.drop_index(op.f('site_pages_site_kind_idx'), table_name='site_pages')
    op.drop_column('site_pages', 'kind')


def downgrade() -> None:
    op.add_column(
        'site_pages',
        sa.Column('kind', sa.TEXT(), server_default=sa.text("'other'::text"), nullable=False),
    )
    op.create_index(op.f('site_pages_site_kind_idx'), 'site_pages', ['site_id', 'kind'])
    op.add_column('seo_page_facts', sa.Column('kind', sa.TEXT(), nullable=True))
