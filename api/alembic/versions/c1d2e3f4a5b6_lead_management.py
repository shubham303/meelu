"""lead management

Revision ID: c1d2e3f4a5b6
Revises: 737bf902de97
Create Date: 2026-09-19

"""
from alembic import op

revision = "c1d2e3f4a5b6"
down_revision = "737bf902de97"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("outreach_message_lead_idx", table_name="outreach_message")
    op.drop_table("outreach_message")

    op.drop_column("outreach_campaign", "angle")
    op.drop_column("outreach_campaign", "cta")
    op.drop_column("outreach_campaign", "tone")
    op.drop_column("outreach_campaign", "followup_days")
    op.drop_column("outreach_lead", "last_message_at")
    op.execute(
        "UPDATE outreach_lead SET stage = 'shortlisted' "
        "WHERE stage NOT IN ('found', 'qualified')"
    )

    op.rename_table("outreach_campaign", "lead_campaign")
    op.execute("ALTER INDEX outreach_campaign_site_idx RENAME TO lead_campaign_site_idx")
    op.execute(
        "ALTER TABLE lead_campaign RENAME CONSTRAINT "
        "outreach_campaign_site_name_key TO lead_campaign_site_name_key"
    )
    op.rename_table("outreach_run", "lead_run")
    op.execute("ALTER INDEX outreach_run_site_idx RENAME TO lead_run_site_idx")
    op.rename_table("outreach_lead", "lead")
    op.execute("ALTER INDEX outreach_lead_site_idx RENAME TO lead_site_idx")


def downgrade() -> None:
    raise NotImplementedError("lead management replaces outreach outright")
