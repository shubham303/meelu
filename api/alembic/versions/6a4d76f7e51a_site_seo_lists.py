"""site_seo lists

Revision ID: 6a4d76f7e51a
Revises: 0f8dd065ea2f
Create Date: 2026-10-06 19:37:57.119506

"""
from alembic import op
import sqlalchemy as sa


revision = '6a4d76f7e51a'
down_revision = '0f8dd065ea2f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('site_seo',
    sa.Column('competitors', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('backlink_opportunities', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', name='site_seo_site_key')
    )


def downgrade() -> None:
    op.drop_table('site_seo')
