"""link suggestion review

Revision ID: d6b8e47c9c69
Revises: 63827d7d19d2
Create Date: 2026-09-19 17:58:13.948837

"""

from alembic import op
import sqlalchemy as sa


revision = "d6b8e47c9c69"
down_revision = "63827d7d19d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "site_link_suggestions",
        sa.Column("review", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
    )
    op.add_column("site_link_suggestions", sa.Column("review_confidence", sa.REAL(), nullable=True))
    op.add_column("site_link_suggestions", sa.Column("review_reason", sa.Text(), nullable=True))
    op.add_column("site_link_suggestions", sa.Column("review_model", sa.Text(), nullable=True))
    op.create_index(
        "site_link_suggestions_review_idx",
        "site_link_suggestions",
        ["site_id", "review"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("site_link_suggestions_review_idx", table_name="site_link_suggestions")
    op.drop_column("site_link_suggestions", "review_model")
    op.drop_column("site_link_suggestions", "review_reason")
    op.drop_column("site_link_suggestions", "review_confidence")
    op.drop_column("site_link_suggestions", "review")
