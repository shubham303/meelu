"""store only genuine backlinks

Revision ID: 45f2950c6b02
Revises: 7b3e9c1d5a20
Create Date: 2026-10-17 20:38:58.860934

"""
from alembic import op
import sqlalchemy as sa


revision = '45f2950c6b02'
down_revision = '7b3e9c1d5a20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(op.f('site_backlinks_genuine_idx'), table_name='site_backlinks')
    op.create_index('site_backlinks_linking_idx', 'site_backlinks', ['site_id', 'backlinking_domain'], unique=False)
    op.drop_column('site_backlinks', 'is_genuine')


def downgrade() -> None:
    op.add_column('site_backlinks', sa.Column('is_genuine', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.drop_index('site_backlinks_linking_idx', table_name='site_backlinks')
    op.create_index(op.f('site_backlinks_genuine_idx'), 'site_backlinks', ['site_id', 'is_genuine', 'backlinking_domain'], unique=False)
