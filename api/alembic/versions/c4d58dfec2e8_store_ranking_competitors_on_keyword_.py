"""store ranking competitors on keyword clusters

Revision ID: c4d58dfec2e8
Revises: 660c2fa04a45
Create Date: 2026-10-17 19:04:51.244243

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4d58dfec2e8'
down_revision = '660c2fa04a45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('seo_keyword_clusters', sa.Column('competitors', sa.ARRAY(sa.Text()), server_default=sa.text("'{}'::text[]"), nullable=False))
    op.execute(
        "UPDATE seo_keyword_clusters k SET competitors = linked.domains "
        "FROM (SELECT l.cluster_id, array_agg(c.domain ORDER BY c.domain) AS domains "
        "FROM seo_keyword_cluster_competitors l JOIN seo_competitors c ON c.id = l.competitor_id "
        "GROUP BY l.cluster_id) linked WHERE k.id = linked.cluster_id"
    )
    op.drop_index(op.f('ix_seo_keyword_cluster_competitors_competitor_id'), table_name='seo_keyword_cluster_competitors')
    op.drop_table('seo_keyword_cluster_competitors')


def downgrade() -> None:
    op.create_table('seo_keyword_cluster_competitors',
    sa.Column('cluster_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.Column('competitor_id', sa.TEXT(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['cluster_id'], ['seo_keyword_clusters.id'], name=op.f('seo_keyword_cluster_competitors_cluster_id_fkey'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['competitor_id'], ['seo_competitors.id'], name=op.f('seo_keyword_cluster_competitors_competitor_id_fkey'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('cluster_id', 'competitor_id', name=op.f('seo_keyword_cluster_competitors_pkey'))
    )
    op.create_index(op.f('ix_seo_keyword_cluster_competitors_competitor_id'), 'seo_keyword_cluster_competitors', ['competitor_id'], unique=False)
    op.drop_column('seo_keyword_clusters', 'competitors')
