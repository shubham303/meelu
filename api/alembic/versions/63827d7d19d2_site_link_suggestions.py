"""site link suggestions

Revision ID: 63827d7d19d2
Revises: 827b6f6ca796
Create Date: 2026-09-19 16:21:42.957813

"""

from alembic import op
import sqlalchemy as sa


revision = "63827d7d19d2"
down_revision = "827b6f6ca796"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_link_suggestions",
        sa.Column("from_page_id", sa.Text(), nullable=False),
        sa.Column("to_page_id", sa.Text(), nullable=False),
        sa.Column("from_chunk_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), server_default=sa.text("'add'"), nullable=False),
        sa.Column("anchor_text", sa.Text(), nullable=True),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("seq", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("site_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["from_chunk_id"], ["site_chunks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_page_id"], ["site_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["site.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_page_id"], ["site_pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "site_id", "from_page_id", "to_page_id", "action", name="site_link_suggestions_edge_idx"
        ),
    )
    op.create_index(
        "site_link_suggestions_from_idx",
        "site_link_suggestions",
        ["site_id", "from_page_id"],
        unique=False,
    )
    op.create_index(
        "site_link_suggestions_state_idx",
        "site_link_suggestions",
        ["site_id", "state"],
        unique=False,
    )
    op.create_index(
        "site_link_suggestions_strategy_idx",
        "site_link_suggestions",
        ["site_id", "strategy"],
        unique=False,
    )
    op.create_index(
        "site_link_suggestions_to_idx",
        "site_link_suggestions",
        ["site_id", "to_page_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("site_link_suggestions_to_idx", table_name="site_link_suggestions")
    op.drop_index("site_link_suggestions_strategy_idx", table_name="site_link_suggestions")
    op.drop_index("site_link_suggestions_state_idx", table_name="site_link_suggestions")
    op.drop_index("site_link_suggestions_from_idx", table_name="site_link_suggestions")
    op.drop_table("site_link_suggestions")
