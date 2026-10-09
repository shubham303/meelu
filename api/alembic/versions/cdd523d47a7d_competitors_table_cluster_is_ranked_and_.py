"""competitors table, cluster is_ranked and competitors

Revision ID: cdd523d47a7d
Revises: 857f3fca42da
Create Date: 2026-10-06 21:02:29.473128

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'cdd523d47a7d'
down_revision = '857f3fca42da'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('seo_competitors',
    sa.Column('domain', sa.Text(), nullable=False),
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('user_id', sa.Text(), nullable=False),
    sa.Column('seq', sa.BigInteger(), sa.Identity(always=False), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('site_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['site_id'], ['site.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('site_id', 'domain', name='seo_competitors_key')
    )
    op.create_index('seo_competitors_site_idx', 'seo_competitors', ['site_id', 'created_at'], unique=False)
    op.create_table('seo_keyword_cluster_competitors',
    sa.Column('cluster_id', sa.Text(), nullable=False),
    sa.Column('competitor_id', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['cluster_id'], ['seo_keyword_clusters.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['competitor_id'], ['seo_competitors.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('cluster_id', 'competitor_id')
    )
    op.create_index(op.f('ix_seo_keyword_cluster_competitors_competitor_id'), 'seo_keyword_cluster_competitors', ['competitor_id'], unique=False)
    op.add_column('seo_keyword_clusters', sa.Column('is_ranked', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.alter_column('seo_keyword_clusters', 'competitors', new_column_name='climb')
    op.execute(
        "INSERT INTO seo_competitors (id, user_id, site_id, domain) "
        "SELECT 'scmp_' || substr(md5(site_seo.site_id || d), 1, 10), site_seo.user_id, site_seo.site_id, d "
        "FROM site_seo, unnest(site_seo.competitors) AS d ON CONFLICT DO NOTHING"
    )
    op.drop_column('site_seo', 'competitors')


def downgrade() -> None:
    op.add_column('site_seo', sa.Column('competitors', postgresql.ARRAY(sa.TEXT()), server_default=sa.text("'{}'::text[]"), autoincrement=False, nullable=False))
    op.alter_column('seo_keyword_clusters', 'climb', new_column_name='competitors')
    op.drop_column('seo_keyword_clusters', 'is_ranked')
    op.drop_index(op.f('ix_seo_keyword_cluster_competitors_competitor_id'), table_name='seo_keyword_cluster_competitors')
    op.drop_table('seo_keyword_cluster_competitors')
    op.drop_index('seo_competitors_site_idx', table_name='seo_competitors')
    op.drop_table('seo_competitors')
