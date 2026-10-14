"""user prompts

Revision ID: e68f7848a9fb
Revises: 6b44bbac7fce
Create Date: 2026-10-14 06:08:04.453463

"""
from alembic import op
import sqlalchemy as sa


revision = 'e68f7848a9fb'
down_revision = '6b44bbac7fce'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('user_prompts',
    sa.Column('surface', sa.Text(), nullable=False),
    sa.Column('label', sa.Text(), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'surface', 'label', name='user_prompts_label_key')
    )
    op.create_index('user_prompts_site_surface_idx', 'user_prompts', ['site_id', 'surface'], unique=False)


def downgrade() -> None:
    op.drop_index('user_prompts_site_surface_idx', table_name='user_prompts')
    op.drop_table('user_prompts')
