import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from src.agent.security import bootstrap, drop_tenants
from src.agent.sql import engine
from src.agent.workspace_expiry import sweep
from src.settings import settings
from tests.integration.agent.test_sql_security import sql, tenant


def relations(schema: str) -> set[str]:
    with engine.begin() as conn:
        return {
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = %s AND c.relkind IN ('r', 'v')",
                (schema,),
            )
        }


def registered(role: str) -> dict[str, datetime]:
    with engine.begin() as conn:
        return dict(
            conn.exec_driver_sql(
                "SELECT table_name, last_used_at FROM agent_workspace_tables WHERE role_name = %s",
                (role,),
            ).fetchall()
        )


async def test_unused_workspace_tables_expire_after_the_ttl(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_data_dir", tmp_path)
    run = uuid.uuid4().hex[:8]
    ctx = await tenant(client, f"ws-x-{run}@example.com", f"x{run}.example.com")
    await asyncio.to_thread(bootstrap)
    try:
        await sql(ctx, "create table weekly as select 1 as n")
        await sql(ctx, "create view weekly_view as select n from weekly")
        await sql(
            ctx,
            "create table _ti_derived_columns (table_key text, column_name text, "
            "primary key (table_key, column_name))",
        )
        await sql(ctx, f"insert into _ti_derived_columns values ('{ctx.schema}.weekly', 'c')")
        models = tmp_path / "models" / ctx.schema
        models.mkdir(parents=True)
        (models / "old.pkl").write_bytes(b"x")

        now = datetime.now(UTC)
        await asyncio.to_thread(sweep, now)
        assert set(await asyncio.to_thread(registered, ctx.role)) == {"weekly", "weekly_view"}
        assert (models / "old.pkl").exists()

        await asyncio.to_thread(sweep, now + timedelta(days=6))
        assert {"weekly", "weekly_view"} <= await asyncio.to_thread(relations, ctx.schema)

        later = now + timedelta(days=settings.agent_workspace_ttl_days, hours=1)
        result = await asyncio.to_thread(sweep, later)
        left = await asyncio.to_thread(relations, ctx.schema)
        assert "weekly" not in left and "weekly_view" not in left
        assert "_ti_derived_columns" in left
        assert f"{ctx.schema}.weekly" in result.dropped
        assert (await sql(ctx, "select count(*) from _ti_derived_columns")).rows == [[0]]
        assert await asyncio.to_thread(registered, ctx.role) == {}
    finally:
        await asyncio.to_thread(drop_tenants, ctx.user_id)


async def test_sweep_runs_tenant_rules_as_the_tenant(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_data_dir", tmp_path)
    run = uuid.uuid4().hex[:8]
    ctx = await tenant(client, f"ws-r-{run}@example.com", f"r{run}.example.com")
    await asyncio.to_thread(bootstrap)
    try:
        await sql(ctx, "create table _ti_column_types (table_key text)")
        await sql(ctx, f"insert into _ti_column_types values ('{ctx.schema}.bait')")
        await sql(ctx, "create table _ti_loot (who text)")
        await sql(
            ctx,
            "create rule spy as on delete to _ti_column_types "
            "do also insert into _ti_loot select current_user::text",
        )
        await sql(ctx, "create table bait as select 1 as n")

        now = datetime.now(UTC)
        await asyncio.to_thread(sweep, now)
        later = now + timedelta(days=settings.agent_workspace_ttl_days, hours=1)
        await asyncio.to_thread(sweep, later)

        assert "bait" not in await asyncio.to_thread(relations, ctx.schema)
        assert (await sql(ctx, "select who from _ti_loot")).rows == [[ctx.role]]
    finally:
        await asyncio.to_thread(drop_tenants, ctx.user_id)


async def test_old_saved_models_expire(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "agent_data_dir", tmp_path)
    models = tmp_path / "models" / "ws_someone"
    models.mkdir(parents=True)
    (models / "churn.pkl").write_bytes(b"x")
    result = await asyncio.to_thread(sweep, datetime.now(UTC) + timedelta(days=8))
    assert "ws_someone/churn.pkl" in result.models
    assert not (models / "churn.pkl").exists()
