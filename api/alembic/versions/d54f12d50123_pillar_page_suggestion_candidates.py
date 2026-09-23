"""pillar page suggestion candidates

Revision ID: d54f12d50123
Revises: e7a1c4b9f012
Create Date: 2026-09-20 12:25:45.074049

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd54f12d50123'
down_revision = 'e7a1c4b9f012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM pillar_page_suggestions")
    op.add_column('pillar_page_suggestions', sa.Column('action', sa.Text(), server_default=sa.text("'create'"), nullable=False))
    op.add_column('pillar_page_suggestions', sa.Column('topic', sa.Text(), nullable=False))
    op.add_column('pillar_page_suggestions', sa.Column('member_page_ids', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'"), nullable=False))
    op.add_column('pillar_page_suggestions', sa.Column('covering_page_id', sa.Text(), nullable=True))
    op.add_column('pillar_page_suggestions', sa.Column('search_score', sa.REAL(), nullable=True))
    op.add_column('pillar_page_suggestions', sa.Column('confidence', sa.REAL(), nullable=True))
    op.add_column('pillar_page_suggestions', sa.Column('score', sa.REAL(), nullable=True))
    op.create_foreign_key('pillar_page_suggestions_covering_page_id_fkey', 'pillar_page_suggestions', 'site_pages', ['covering_page_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('pillar_page_suggestions_covering_page_id_fkey', 'pillar_page_suggestions', type_='foreignkey')
    op.drop_column('pillar_page_suggestions', 'score')
    op.drop_column('pillar_page_suggestions', 'confidence')
    op.drop_column('pillar_page_suggestions', 'search_score')
    op.drop_column('pillar_page_suggestions', 'covering_page_id')
    op.drop_column('pillar_page_suggestions', 'member_page_ids')
    op.drop_column('pillar_page_suggestions', 'topic')
    op.drop_column('pillar_page_suggestions', 'action')
