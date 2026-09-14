"""drop seo desk tables

Revision ID: b6992cce3f50
Revises: 9f6933cd1bf2
Create Date: 2026-09-13 23:48:32.566055

"""
from alembic import op

revision = 'b6992cce3f50'
down_revision = '9f6933cd1bf2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DROP TABLE IF EXISTS "
        + ", ".join(
            (
                "seo_runs",
                "seo_ai_trend_points",
                "seo_plans",
                "keyword_trend_points",
                "seo_ai_pages",
                "seo_competitors",
                "seo_opportunities",
                "seo_findings",
                "seo_ledger",
                "seo_plan_groups",
                "seo_structural_checks",
                "seo_vendor_calls",
                "seo_rank_snapshots",
                "seo_measurements",
                "seo_ai_shares",
                "domain_rankings",
                "keyword_volume_months",
                "seo_rank_trackers",
                "seo_ai_snapshots",
                "seo_finding_facts",
                "seo_calibration",
                "seo_clusters",
                "seo_plan_steps",
                "seo_opportunity_evidence",
                "seo_page_vitals",
                "seo_budgets",
                "serp_snapshots",
                "serp_results",
                "seo_structural_proposals",
                "seo_cluster_pages",
                "seo_keywords",
                "keyword_facts",
            )
        )
        + " CASCADE"
    )


def downgrade() -> None:
    raise NotImplementedError("the seo desk is gone; rebuild from the baseline")
