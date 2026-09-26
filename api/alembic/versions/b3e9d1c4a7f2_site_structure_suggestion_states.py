"""site_structure suggestion states, chunk-aware link key, pillar member_key

Revision ID: b3e9d1c4a7f2
Revises: a5823eedc033
Create Date: 2026-09-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b3e9d1c4a7f2'
down_revision = 'a5823eedc033'
branch_labels = None
depends_on = None

TABLES = ('link_suggestions', 'pillar_page_suggestions')


def upgrade() -> None:
    for table in TABLES:
        op.execute(f"delete from {table} where state in ('done', 'stale')")
        op.execute(f"update {table} set state = 'review_approved' where state = 'ready'")
        op.execute(f"update {table} set state = 'review_rejected' where state = 'llm_rejected'")

    op.drop_constraint('link_suggestions_edge_idx', 'link_suggestions', type_='unique')
    op.execute(
        "alter table link_suggestions add constraint link_suggestions_edge_idx "
        "unique nulls not distinct (site_id, from_page_id, from_chunk_id, to_page_id, action)"
    )
    op.drop_constraint('link_suggestions_from_chunk_id_fkey', 'link_suggestions', type_='foreignkey')
    op.create_foreign_key(
        'link_suggestions_from_chunk_id_fkey',
        'link_suggestions',
        'site_chunks',
        ['from_chunk_id'],
        ['id'],
        ondelete='CASCADE',
    )

    op.execute(
        "update pillar_page_suggestions set member_page_ids = array("
        "select m from (select distinct unnest(member_page_ids) as m) d order by m collate \"C\")"
    )
    op.add_column('pillar_page_suggestions', sa.Column('member_key', sa.Text(), nullable=True))
    op.execute(
        "update pillar_page_suggestions set member_key = encode(sha256(convert_to("
        "array_to_string(member_page_ids, ','), 'UTF8')), 'hex')"
    )
    op.execute(
        "delete from pillar_page_suggestions p using pillar_page_suggestions keep "
        "where p.site_id = keep.site_id and p.member_key = keep.member_key and p.seq > keep.seq"
    )
    op.alter_column('pillar_page_suggestions', 'member_key', nullable=False)
    op.create_unique_constraint(
        'pillar_page_suggestions_members_idx', 'pillar_page_suggestions', ['site_id', 'member_key']
    )


def downgrade() -> None:
    op.drop_constraint('pillar_page_suggestions_members_idx', 'pillar_page_suggestions', type_='unique')
    op.drop_column('pillar_page_suggestions', 'member_key')

    op.drop_constraint('link_suggestions_from_chunk_id_fkey', 'link_suggestions', type_='foreignkey')
    op.create_foreign_key(
        'link_suggestions_from_chunk_id_fkey',
        'link_suggestions',
        'site_chunks',
        ['from_chunk_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.drop_constraint('link_suggestions_edge_idx', 'link_suggestions', type_='unique')
    op.execute(
        "delete from link_suggestions l using link_suggestions keep "
        "where l.site_id = keep.site_id and l.from_page_id = keep.from_page_id "
        "and l.to_page_id = keep.to_page_id and l.action = keep.action and l.seq > keep.seq"
    )
    op.create_unique_constraint(
        'link_suggestions_edge_idx',
        'link_suggestions',
        ['site_id', 'from_page_id', 'to_page_id', 'action'],
    )

    for table in TABLES:
        op.execute(f"update {table} set state = 'ready' where state = 'review_approved'")
        op.execute(
            f"update {table} set state = 'llm_rejected' "
            "where state in ('review_rejected', 'screening_rejected')"
        )
        op.execute(f"update {table} set state = 'draft' where state = 'screening_approved'")
