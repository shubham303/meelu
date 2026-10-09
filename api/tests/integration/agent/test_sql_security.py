import asyncio
import uuid

import psycopg
import pytest
from sqlalchemy.engine import make_url

from src.agent.context import AgentContext, reset_context, set_context
from src.agent.security import bootstrap, ensure_user
from src.agent.sql import engine
from src.agent.tools.core import run_sql
from src.agent.workspace import workspace_tables
from src.settings import settings
from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

CHILD_TABLE = "agent_scope_probe_child"


async def tenant(client, email, domain):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": "Site"})
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    await seed_pages(site_id, user_id, [{"url": f"https://{domain}/", "depth": 0}])
    role, schema = await asyncio.to_thread(ensure_user, user_id)
    return AgentContext(
        user_id=user_id,
        site_id=site_id,
        site_domain=domain,
        site_status="active",
        role=role,
        schema=schema,
        api_key="",
    )


async def sql(ctx: AgentContext, query: str):
    token = set_context(ctx)
    try:
        return await asyncio.to_thread(run_sql, query)
    finally:
        reset_context(token)


@pytest.fixture
async def pair(client):
    run = uuid.uuid4().hex[:8]
    a = await tenant(client, f"sql-a-{run}@example.com", f"a{run}.example.com")
    b = await tenant(client, f"sql-b-{run}@example.com", f"b{run}.example.com")
    await asyncio.to_thread(bootstrap)
    return a, b


async def test_agent_runs_as_its_own_login_role(pair):
    a, _ = pair
    result = await sql(a, "select current_user, session_user")
    assert result.rows == [[a.role, a.role]]


async def test_agent_cannot_switch_back_to_the_admin_role(pair):
    a, _ = pair
    admin = make_url(settings.database_url).username
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, f"select set_config('role', '{admin}', true)")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "delete from site_pages")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "select * from agent_tenants")


async def test_one_statement_per_call(pair):
    a, _ = pair
    with pytest.raises(psycopg.errors.SyntaxError):
        await sql(a, "select 1; select 2")
    assert (await sql(a, "select '100%' as v")).rows == [["100%"]]


async def test_rows_stay_with_their_owner_even_when_the_setting_is_forged(pair):
    a, b = pair
    own = f"select count(*) from site_pages where site_id = '{a.site_id}'"
    other = f"select count(*) from site_pages where site_id = '{b.site_id}'"
    assert (await sql(a, own)).rows == [[1]]
    assert (await sql(a, other)).rows == [[0]]
    forged = (
        f"select count(*) from site_pages "
        f"where set_config('meelu.user_id', '{b.user_id}', true) is not null"
    )
    assert (await sql(a, forged)).rows == [[1]]


def create_child_table() -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(
            f"CREATE TABLE {CHILD_TABLE} (id text PRIMARY KEY, "
            "page_id text NOT NULL REFERENCES site_pages(id) ON DELETE CASCADE)"
        )


def drop_child_table() -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(f"DROP TABLE IF EXISTS {CHILD_TABLE}")


async def test_child_tables_without_user_id_are_scoped_through_their_parent(pair):
    a, _ = pair
    await asyncio.to_thread(create_child_table)
    try:
        granted = (await asyncio.to_thread(bootstrap)).granted
        assert CHILD_TABLE in granted
        assert "alembic_version" not in granted
        assert (await sql(a, f"select count(*) from {CHILD_TABLE}")).rows == [[0]]
    finally:
        await asyncio.to_thread(drop_child_table)
        await asyncio.to_thread(bootstrap)


async def test_agent_cannot_write_into_another_workspace(pair):
    a, b = pair
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, f'create table "{b.schema}".stolen (x int)')


async def test_workspace_reads_run_as_the_tenant(pair):
    a, _ = pair
    await sql(
        a,
        "create function whoami() returns text language sql as $$ select current_user::text $$",
    )
    await sql(a, "create view probe as select whoami() as who")
    rows = await workspace_tables.rows(a.user_id, "probe")
    assert rows == [{"who": a.role}]


async def test_workspace_reads_are_capped(pair, monkeypatch):
    a, _ = pair
    await sql(a, "create table big as select generate_series(1, 3) as n")
    monkeypatch.setattr(settings, "agent_max_workspace_rows", 2)
    with pytest.raises(ValueError, match="more than 2 rows"):
        await workspace_tables.rows(a.user_id, "big")
    with pytest.raises(ValueError, match="Could not read"):
        await workspace_tables.rows(a.user_id, "missing")
