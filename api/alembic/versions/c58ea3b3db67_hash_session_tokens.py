"""hash session tokens

Revision ID: c58ea3b3db67
Revises: 29aa8084d6df
Create Date: 2026-10-10 01:00:18.313865

"""
from alembic import op
import sqlalchemy as sa


revision = 'c58ea3b3db67'
down_revision = '29aa8084d6df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('DELETE FROM access_token')
    op.drop_column('access_token', 'token')
    op.add_column('access_token', sa.Column('token_hash', sa.String(length=64), nullable=False))
    op.create_primary_key('access_token_pkey', 'access_token', ['token_hash'])


def downgrade() -> None:
    op.execute('DELETE FROM access_token')
    op.drop_column('access_token', 'token_hash')
    op.add_column('access_token', sa.Column('token', sa.VARCHAR(length=43), nullable=False))
    op.create_primary_key('access_token_pkey', 'access_token', ['token'])
