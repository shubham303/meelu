import asyncio
import uuid

import psycopg
import pytest
from sqlalchemy.engine import make_url

from src.agent.context import AgentContext, reset_context, set_context
from src.agent.security import (
    READ_ROLE,
    bootstrap,
    drop_orphan_tenants,
    drop_tenants,
    ensure_tenant,
)
from src.agent.sql import engine
from src.agent.tools.core import run_sql
from src.agent.workspace import workspace_tables
from src.settings import settings
from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

CHILD_TABLE = "agent_scope_probe_child"


async def tenant(client, email, domain):
    await signup(client, email)
    return await site_tenant(client, await user_id_of(email), domain)


async def site_tenant(client, user_id, domain):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": "Site"})
    assert r.status_code == 201, r.text
    site_id = r.json()["data"]["id"]
    await seed_pages(site_id, user_id, [{"url": f"https://{domain}/", "depth": 0}])
    role, schema = await asyncio.to_thread(ensure_tenant, user_id, site_id)
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
    yield a, b
    for ctx in (a, b):
        await asyncio.to_thread(drop_tenants, ctx.user_id)


def role_exists(role: str) -> bool:
    with engine.begin() as conn:
        found = conn.exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
        return found.fetchone() is not None


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


async def test_only_listed_tables_are_readable(pair):
    a, _ = pair
    await asyncio.to_thread(create_child_table)
    try:
        granted = (await asyncio.to_thread(bootstrap)).granted
        assert CHILD_TABLE not in granted
        for table in ("payment", "credit_ledger", "provider_call", "api_keys", "user"):
            assert table not in granted
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                await sql(a, f'select count(*) from "{table}"')
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await sql(a, f"select count(*) from {CHILD_TABLE}")
    finally:
        await asyncio.to_thread(drop_child_table)
        await asyncio.to_thread(bootstrap)


async def test_child_tables_without_user_id_are_scoped_through_their_parent(pair):
    a, _ = pair
    granted = (await asyncio.to_thread(bootstrap)).granted
    assert "seo_keyword_cluster_competitors" in granted
    assert (await sql(a, "select count(*) from seo_keyword_cluster_competitors")).rows == [[0]]


async def test_agent_cannot_write_into_another_workspace(pair):
    a, b = pair
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, f'create table "{b.schema}".stolen (x int)')


def test_app_connects_without_superuser():
    with engine.begin() as conn:
        row = conn.exec_driver_sql(
            "SELECT rolsuper, rolbypassrls, rolcreaterole FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
    assert tuple(row) == (False, False, True)


async def test_agent_cannot_create_functions_or_large_objects(pair):
    a, _ = pair
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "create function f() returns int language sql as $$ select 1 $$")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "do $$ begin perform 1; end $$")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "select lo_from_bytea(0, 'x'::bytea)")
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "select pg_advisory_xact_lock(hashtext('credit_spend:x'))")


async def test_query_cannot_switch_off_its_timeout(pair, monkeypatch):
    a, _ = pair
    monkeypatch.setattr(settings, "agent_statement_timeout_ms", 1000)
    with pytest.raises(psycopg.errors.QueryCanceled):
        await sql(
            a,
            "select set_config('statement_timeout', '0', true), "
            "pg_sleep(case when g > 60 then 2 else 0 end) from generate_series(1, 100) g",
        )


async def test_tenant_limits_cannot_be_raised(pair):
    a, _ = pair
    assert (await sql(a, "show temp_file_limit")).rows == [["1GB"]]
    assert (await sql(a, "show hash_mem_multiplier")).rows == [["2"]]
    assert (await sql(a, "show maintenance_work_mem")).rows == [["64MB"]]
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        await sql(a, "set temp_file_limit = -1")


async def test_large_results_are_refused(pair):
    a, _ = pair
    with pytest.raises(ValueError, match="larger than"):
        await sql(a, "select repeat('x', 1024 * 1024) from generate_series(1, 10)")
    result = await sql(a, "select g from generate_series(1, 100000) g")
    assert result.truncated and result.row_count == 200


async def test_full_workspace_refuses_more_sql(pair, monkeypatch):
    a, _ = pair
    await sql(
        a, "create table filler as select repeat('x', 1000) as v from generate_series(1, 100)"
    )
    monkeypatch.setattr(settings, "agent_max_workspace_bytes", 1024)
    with pytest.raises(ValueError, match="quota"):
        await sql(a, "select 1")


async def test_dropping_a_user_removes_its_role_and_schema(client):
    run = uuid.uuid4().hex[:8]
    ctx = await tenant(client, f"sql-d-{run}@example.com", f"d{run}.example.com")
    await sql(ctx, "create table kept as select 1 as n")
    await asyncio.to_thread(drop_tenants, ctx.user_id)
    assert not await asyncio.to_thread(role_exists, ctx.role)


async def test_each_site_of_one_user_sees_only_its_own_rows_and_workspace(client):
    run = uuid.uuid4().hex[:8]
    first = await tenant(client, f"sql-s-{run}@example.com", f"s1{run}.example.com")
    second = await site_tenant(client, first.user_id, f"s2{run}.example.com")
    await asyncio.to_thread(bootstrap)
    try:
        assert first.role != second.role and first.schema != second.schema
        assert (await sql(first, "select count(*) from site_pages")).rows == [[1]]
        assert (await sql(first, "select id from site")).rows == [[first.site_id]]
        assert (await sql(second, "select id from site")).rows == [[second.site_id]]
        other = f"select count(*) from site_pages where site_id = '{second.site_id}'"
        assert (await sql(first, other)).rows == [[0]]
        await sql(second, "create table mine as select 1 as n")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            await sql(first, f'select * from "{second.schema}".mine')
    finally:
        await asyncio.to_thread(drop_tenants, first.user_id)


async def test_deleting_a_site_leaves_an_orphan_role_the_sweep_drops(client):
    run = uuid.uuid4().hex[:8]
    ctx = await tenant(client, f"sql-o-{run}@example.com", f"o{run}.example.com")
    r = await client.delete(f"/api/v1/sites/{ctx.site_id}")
    assert r.status_code in (200, 204), r.text
    assert await asyncio.to_thread(role_exists, ctx.role)
    assert ctx.role in await asyncio.to_thread(drop_orphan_tenants)
    assert not await asyncio.to_thread(role_exists, ctx.role)


def make_foreign_role(role: str) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(f'CREATE ROLE "{role}" NOLOGIN IN ROLE {READ_ROLE}')


def drop_role(role: str) -> None:
    with engine.begin() as conn:
        conn.exec_driver_sql(f'DROP ROLE IF EXISTS "{role}"')


async def test_the_sweep_leaves_tenants_of_other_databases_alone():
    role = f"agent_elsewhere_{uuid.uuid4().hex[:12]}"
    await asyncio.to_thread(make_foreign_role, role)
    try:
        assert role not in await asyncio.to_thread(drop_orphan_tenants)
        assert await asyncio.to_thread(role_exists, role)
    finally:
        await asyncio.to_thread(drop_role, role)


async def test_workspace_reads_run_as_the_tenant(pair):
    a, _ = pair
    await sql(a, "create view probe as select current_user::text as who")
    rows = await workspace_tables.rows(a.user_id, a.site_id, "probe")
    assert rows == [{"who": a.role}]


async def test_workspace_reads_are_capped(pair, monkeypatch):
    a, _ = pair
    await sql(a, "create table big as select generate_series(1, 3) as n")
    monkeypatch.setattr(settings, "agent_max_workspace_rows", 2)
    with pytest.raises(ValueError, match="more than 2 rows"):
        await workspace_tables.rows(a.user_id, a.site_id, "big")
    with pytest.raises(ValueError, match="Could not read"):
        await workspace_tables.rows(a.user_id, a.site_id, "missing")


async def test_shared_social_posts_show_only_through_the_site(pair):
    a, b = pair
    run = uuid.uuid4().hex[:8]
    with engine.begin() as conn:
        for name in ("mine", "theirs", "loose"):
            conn.exec_driver_sql(
                "INSERT INTO social_post (id, post_key, platform, url, text) "
                "VALUES (%s, %s, 'hackernews', 'https://news.ycombinator.com', 'post')",
                (f"sp_{name}_{run}", f"hackernews:{name}-{run}"),
            )
        for ctx, name in ((a, "mine"), (b, "theirs")):
            conn.exec_driver_sql(
                "INSERT INTO social_listening_post (id, user_id, site_id, post_id, status) "
                "VALUES (%s, %s, %s, %s, 'to_reply')",
                (f"slp_{name}_{run}", ctx.user_id, ctx.site_id, f"sp_{name}_{run}"),
            )
    seen = await sql(a, f"select id from social_post where id like '%{run}' order by id")
    assert seen.rows == [[f"sp_mine_{run}"]]
