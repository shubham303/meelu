"""site markets and language replace country

Revision ID: 2b7bcc1b10b8
Revises: f164a2b0e67b
Create Date: 2026-10-06 19:58:07.946033

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2b7bcc1b10b8'
down_revision = 'f164a2b0e67b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('site', sa.Column('markets', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), nullable=False))
    op.add_column('site', sa.Column('language', sa.Text(), nullable=True))
    op.drop_column('site', 'country')


def downgrade() -> None:
    op.add_column('site', sa.Column('country', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_column('site', 'language')
    op.drop_column('site', 'markets')
