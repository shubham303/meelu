"""issue llm check

Revision ID: 9f6933cd1bf2
Revises: 61fa53e5d78a
Create Date: 2026-09-13 15:52:56.434726

"""
from alembic import op
import sqlalchemy as sa


revision = '9f6933cd1bf2'
down_revision = '61fa53e5d78a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_issues', sa.Column('llm_check_required', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('site_issues', sa.Column('llm_check_done_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('site_page_issues', sa.Column('llm_check_required', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('site_page_issues', sa.Column('llm_check_done_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('site_page_issues', 'llm_check_done_at')
    op.drop_column('site_page_issues', 'llm_check_required')
    op.drop_column('site_issues', 'llm_check_done_at')
    op.drop_column('site_issues', 'llm_check_required')
