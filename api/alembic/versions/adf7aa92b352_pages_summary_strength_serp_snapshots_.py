"""pages summary strength, serp snapshots, reach precheck

Revision ID: adf7aa92b352
Revises: 215b81ec4d5c
Create Date: 2026-09-29 21:59:53.408631

"""
from alembic import op
import sqlalchemy as sa


revision = 'adf7aa92b352'
down_revision = '215b81ec4d5c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM seo_reach_queries")
    op.execute("DELETE FROM seo_serps")
    op.execute("DELETE FROM seo_pages")
    op.execute("DELETE FROM seo_domains")
    op.add_column('seo_domains', sa.Column('referring_main_domains', sa.BigInteger(), nullable=True))
    op.add_column('seo_domains', sa.Column('referring_main_domains_nofollow', sa.BigInteger(), nullable=True))
    op.add_column('seo_domains', sa.Column('spam_score', sa.Integer(), nullable=True))
    op.add_column('seo_domains', sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True))
    op.add_column('seo_pages', sa.Column('main_domain_rank', sa.Integer(), nullable=True))
    op.add_column('seo_pages', sa.Column('referring_main_domains', sa.BigInteger(), nullable=True))
    op.add_column('seo_pages', sa.Column('referring_main_domains_nofollow', sa.BigInteger(), nullable=True))
    op.add_column('seo_pages', sa.Column('spam_score', sa.Integer(), nullable=True))
    op.add_column('seo_pages', sa.Column('first_seen', sa.DateTime(timezone=True), nullable=True))
    op.add_column('seo_reach_queries', sa.Column('precheck_likely_position', sa.Integer(), nullable=True))
    op.add_column('seo_reach_queries', sa.Column('precheck_expected_position', sa.REAL(), nullable=True))
    op.add_column('seo_reach_queries', sa.Column('snapshot_captured_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('seo_reach_queries', sa.Column('serp_agreement', sa.REAL(), nullable=True))
    op.add_column('seo_reach_queries', sa.Column('scale', sa.REAL(), nullable=False))
    op.add_column('seo_serps', sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False))


def downgrade() -> None:
    op.drop_column('seo_serps', 'captured_at')
    op.drop_column('seo_reach_queries', 'scale')
    op.drop_column('seo_reach_queries', 'serp_agreement')
    op.drop_column('seo_reach_queries', 'snapshot_captured_at')
    op.drop_column('seo_reach_queries', 'precheck_expected_position')
    op.drop_column('seo_reach_queries', 'precheck_likely_position')
    op.drop_column('seo_pages', 'first_seen')
    op.drop_column('seo_pages', 'spam_score')
    op.drop_column('seo_pages', 'referring_main_domains_nofollow')
    op.drop_column('seo_pages', 'referring_main_domains')
    op.drop_column('seo_pages', 'main_domain_rank')
    op.drop_column('seo_domains', 'first_seen')
    op.drop_column('seo_domains', 'spam_score')
    op.drop_column('seo_domains', 'referring_main_domains_nofollow')
    op.drop_column('seo_domains', 'referring_main_domains')
