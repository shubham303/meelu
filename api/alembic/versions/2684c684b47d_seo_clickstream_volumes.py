"""seo clickstream volumes

Revision ID: 2684c684b47d
Revises: 2f4d93bbd8e0
Create Date: 2026-10-02 15:01:07.334806

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '2684c684b47d'
down_revision = '2f4d93bbd8e0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_clickstream_volumes',
    sa.Column('keyword', sa.Text(), nullable=False),
    sa.Column('location_code', sa.Integer(), nullable=False),
    sa.Column('language_code', sa.Text(), nullable=False),
    sa.Column('search_volume', sa.Integer(), nullable=True),
    sa.Column('monthly_searches', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('keyword', 'location_code', 'language_code')
    )
    op.create_index('seo_clickstream_volumes_expires_idx', 'seo_clickstream_volumes', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_index('seo_clickstream_volumes_expires_idx', table_name='seo_clickstream_volumes')
    op.drop_table('seo_clickstream_volumes')
