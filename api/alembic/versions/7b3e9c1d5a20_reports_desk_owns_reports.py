"""reports desk owns reports

Revision ID: 7b3e9c1d5a20
Revises: 46a44f418e78
Create Date: 2026-10-17 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "7b3e9c1d5a20"
down_revision = "46a44f418e78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("analytics_reports", "reports")
    op.execute("ALTER SEQUENCE analytics_reports_seq_seq RENAME TO reports_seq_seq")
    op.execute("ALTER TABLE reports RENAME CONSTRAINT analytics_reports_pkey TO reports_pkey")
    op.execute(
        "ALTER TABLE reports RENAME CONSTRAINT analytics_reports_site_id_fkey "
        "TO reports_site_id_fkey"
    )
    op.execute(
        "ALTER TABLE reports RENAME CONSTRAINT analytics_reports_user_id_fkey "
        "TO reports_user_id_fkey"
    )
    op.drop_index("analytics_reports_site_idx", table_name="reports")
    op.drop_index("analytics_reports_user_idx", table_name="reports")
    op.add_column(
        "reports",
        sa.Column("desk", sa.Text(), nullable=False, server_default=sa.text("'analytics'")),
    )
    op.alter_column("reports", "desk", server_default=None)
    op.create_index("reports_site_idx", "reports", ["user_id", "site_id", "created_at"])
    op.create_index("reports_desk_idx", "reports", ["site_id", "desk", "created_at"])


def downgrade() -> None:
    op.drop_index("reports_desk_idx", table_name="reports")
    op.drop_index("reports_site_idx", table_name="reports")
    op.drop_column("reports", "desk")
    op.create_index("analytics_reports_user_idx", "reports", ["user_id", "created_at"])
    op.create_index("analytics_reports_site_idx", "reports", ["site_id", "created_at"])
    op.execute(
        "ALTER TABLE reports RENAME CONSTRAINT reports_user_id_fkey "
        "TO analytics_reports_user_id_fkey"
    )
    op.execute(
        "ALTER TABLE reports RENAME CONSTRAINT reports_site_id_fkey "
        "TO analytics_reports_site_id_fkey"
    )
    op.execute("ALTER TABLE reports RENAME CONSTRAINT reports_pkey TO analytics_reports_pkey")
    op.execute("ALTER SEQUENCE reports_seq_seq RENAME TO analytics_reports_seq_seq")
    op.rename_table("reports", "analytics_reports")
