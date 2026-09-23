"""drop link suggestion strategy

Revision ID: 618c56a9befd
Revises: d6b8e47c9c69
Create Date: 2026-09-19 23:00:35.563783

"""

from alembic import op
import sqlalchemy as sa


revision = "618c56a9befd"
down_revision = "d6b8e47c9c69"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE site_link_suggestions SET review = 'auto_rejected' WHERE review = 'llm_rejected'"
    )
    op.drop_index(op.f("site_link_suggestions_strategy_idx"), table_name="site_link_suggestions")
    op.drop_column("site_link_suggestions", "strategy")


def downgrade() -> None:
    op.add_column(
        "site_link_suggestions",
        sa.Column("strategy", sa.TEXT(), autoincrement=False, nullable=False),
    )
    op.create_index(
        op.f("site_link_suggestions_strategy_idx"),
        "site_link_suggestions",
        ["site_id", "strategy"],
        unique=False,
    )
