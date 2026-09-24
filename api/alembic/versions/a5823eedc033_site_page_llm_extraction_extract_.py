"""site_page_llm_extraction extract_attempts

Revision ID: a5823eedc033
Revises: a1c7f4e93b20
Create Date: 2026-09-24 11:39:45.211297

"""
from alembic import op
import sqlalchemy as sa


revision = 'a5823eedc033'
down_revision = 'a1c7f4e93b20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site_page_llm_extraction', sa.Column('extract_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False))


def downgrade() -> None:
    op.drop_column('site_page_llm_extraction', 'extract_attempts')
