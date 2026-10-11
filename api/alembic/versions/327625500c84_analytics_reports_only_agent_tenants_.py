"""analytics reports only, agent tenants per site, workspace table registry

Revision ID: 327625500c84
Revises: ac13acf8832e
Create Date: 2026-10-10 18:24:50.816252

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "327625500c84"
down_revision = "ac13acf8832e"
branch_labels = None
depends_on = None


def _drop_tenant_roles() -> None:
    bind = op.get_bind()
    for (role,) in bind.exec_driver_sql("SELECT role_name FROM agent_tenants").fetchall():
        if (
            bind.exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).first()
            is None
        ):
            continue
        quoted = '"' + role.replace('"', '""') + '"'
        bind.exec_driver_sql(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = %s", (role,)
        )
        bind.exec_driver_sql(f"DROP OWNED BY {quoted} CASCADE")
        bind.exec_driver_sql(f"DROP ROLE {quoted}")
    bind.exec_driver_sql("DELETE FROM agent_tenants")


def upgrade() -> None:
    _drop_tenant_roles()
    op.drop_index(op.f("analytics_reports_session_idx"), table_name="analytics_reports")
    op.drop_constraint(
        op.f("analytics_reports_session_id_fkey"), "analytics_reports", type_="foreignkey"
    )
    op.drop_column("analytics_reports", "session_id")
    op.create_table(
        "agent_workspace_tables",
        sa.Column("role_name", sa.Text(), nullable=False),
        sa.Column("table_name", sa.Text(), nullable=False),
        sa.Column("activity", sa.BigInteger(), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["role_name"], ["agent_tenants.role_name"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_name", "table_name"),
    )
    op.drop_index(op.f("analytics_sources_session_idx"), table_name="analytics_sources")
    op.drop_index(op.f("analytics_sources_user_idx"), table_name="analytics_sources")
    op.drop_table("analytics_sources")
    op.drop_index(op.f("analytics_sessions_site_idx"), table_name="analytics_sessions")
    op.drop_index(op.f("analytics_sessions_user_idx"), table_name="analytics_sessions")
    op.drop_table("analytics_sessions")
    op.add_column("agent_tenants", sa.Column("schema_name", sa.Text(), nullable=False))
    op.add_column("agent_tenants", sa.Column("site_id", sa.Text(), nullable=False))
    op.drop_constraint(op.f("agent_tenants_user_id_key"), "agent_tenants", type_="unique")
    op.create_unique_constraint(
        "agent_tenants_user_site_key", "agent_tenants", ["user_id", "site_id"]
    )
    op.create_unique_constraint("agent_tenants_schema_name_key", "agent_tenants", ["schema_name"])
    op.create_foreign_key(
        "agent_tenants_site_id_fkey",
        "agent_tenants",
        "site",
        ["site_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    _drop_tenant_roles()
    op.add_column(
        "analytics_reports", sa.Column("session_id", sa.TEXT(), autoincrement=False, nullable=True)
    )
    op.create_foreign_key(
        op.f("analytics_reports_session_id_fkey"),
        "analytics_reports",
        "analytics_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("analytics_reports_session_idx"),
        "analytics_reports",
        ["session_id", "created_at"],
        unique=False,
    )
    op.drop_constraint("agent_tenants_site_id_fkey", "agent_tenants", type_="foreignkey")
    op.drop_constraint("agent_tenants_schema_name_key", "agent_tenants", type_="unique")
    op.drop_constraint("agent_tenants_user_site_key", "agent_tenants", type_="unique")
    op.create_unique_constraint(
        op.f("agent_tenants_user_id_key"),
        "agent_tenants",
        ["user_id"],
        postgresql_nulls_not_distinct=False,
    )
    op.drop_column("agent_tenants", "site_id")
    op.drop_column("agent_tenants", "schema_name")
    op.create_table(
        "analytics_sources",
        sa.Column("session_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("name", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("file_path", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "seq",
            sa.BIGINT(),
            sa.Identity(
                always=False,
                start=1,
                increment=1,
                minvalue=1,
                maxvalue=9223372036854775807,
                cycle=False,
                cache=1,
            ),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("site_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analytics_sessions.id"],
            name=op.f("analytics_sources_session_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
            name=op.f("analytics_sources_site_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("analytics_sources_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("analytics_sources_pkey")),
    )
    op.create_index(
        op.f("analytics_sources_user_idx"),
        "analytics_sources",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("analytics_sources_session_idx"),
        "analytics_sources",
        ["session_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "analytics_sessions",
        sa.Column("title", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "about",
            sa.TEXT(),
            server_default=sa.text("''::text"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("session_key", sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column("id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column(
            "seq",
            sa.BIGINT(),
            sa.Identity(
                always=False,
                start=1,
                increment=1,
                minvalue=1,
                maxvalue=9223372036854775807,
                cycle=False,
                cache=1,
            ),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("site_id", sa.TEXT(), autoincrement=False, nullable=False),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["site.id"],
            name=op.f("analytics_sessions_site_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("analytics_sessions_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("analytics_sessions_pkey")),
    )
    op.create_index(
        op.f("analytics_sessions_user_idx"),
        "analytics_sessions",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("analytics_sessions_site_idx"),
        "analytics_sessions",
        ["site_id", "created_at"],
        unique=False,
    )
    op.drop_table("agent_workspace_tables")
