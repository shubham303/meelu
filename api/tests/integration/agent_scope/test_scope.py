import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

import src.core.tables  # noqa: F401
from src.agent.security import BLOCKED_TABLES
from src.agent_scope.lib import SiteRef
from src.agent_scope.registry import (
    AGENT_SCOPES,
    DESK_NAMES,
    WRITE_TOOL_NAMES,
    desk_writes,
)
from src.agent_scope.service import render_tables, resolve_scope, scope_response
from src.core.orm import Base
from tests.conftest import signup

SITE = SiteRef(id="site_scope_0001", name="Acme Coffee Gear", domain="acmecoffeegear.example")


def test_every_scope_lists_real_unblocked_tables():
    for action, scope in AGENT_SCOPES.items():
        assert scope.desk in DESK_NAMES, action
        if scope.tables is None:
            continue
        names = {t.__tablename__ for t in scope.tables}
        assert names <= set(Base.metadata.tables), action
        assert not names & BLOCKED_TABLES, action


def test_render_tables_lists_the_scopes_columns():
    text = render_tables(AGENT_SCOPES["profile-setup"].tables)
    assert "## The database" in text
    assert "- notes: " in text
    full = render_tables(None)
    assert "- site_pages: " in full
    for blocked in BLOCKED_TABLES:
        assert f"- {blocked}: " not in full


def test_every_action_writes_through_registered_tools():
    for action, scope in AGENT_SCOPES.items():
        assert set(scope.write_names) <= WRITE_TOOL_NAMES, action
        assert scope.desk in DESK_NAMES, action


@pytest.mark.parametrize("action", sorted(AGENT_SCOPES))
def test_payload_shape(action):
    scope = AGENT_SCOPES[action]
    body = scope_response(action, scope, None if scope.is_global else SITE).model_dump(
        by_alias=True
    )
    assert isinstance(body["providers"], list)
    assert body["desk"] == scope.desk
    assert all(isinstance(w, str) for w in body["writes"])
    creates = body["createToolName"]
    if creates is not None:
        for name in [creates] if isinstance(creates, str) else creates:
            assert name.startswith("mcp__meelu__")
            assert name.removeprefix("mcp__meelu__") in body["writes"]
    assert isinstance(body["systemPrompt"], str) and body["systemPrompt"]


def test_profile_setup_sees_only_the_profile():
    scope = AGENT_SCOPES["profile-setup"]
    assert scope.desk == "profile"
    assert scope.table_names == {"profile", "notes"}
    assert scope_response("profile-setup", scope, None).writes == [
        "save_profile",
        "clear_profile_fields",
    ]


def test_desk_writes_union_the_desks_actions():
    assert desk_writes("site") == {
        "create_site_issue",
        "reject_issue",
        "restore_issue",
        "save_note",
        "update_note",
        "delete_note",
    }
    assert desk_writes("outreach") == {"save_note", "update_note", "delete_note"}


def test_scope_response_merges_added_desks():
    base = scope_response("issue-review", AGENT_SCOPES["issue-review"], SITE)
    assert [d.name for d in base.desks] == [
        "analytics",
        "content",
        "outreach",
        "pages",
        "profile",
        "site",
    ]
    merged = scope_response("issue-review", AGENT_SCOPES["issue-review"], SITE, "content,analytics")
    assert "content_create_piece" in merged.writes
    assert "analytics" in merged.mcp_servers
    assert "content_pieces" in merged.system_prompt
    assert [d.name for d in merged.desks] == ["outreach", "pages", "profile", "site"]
    with pytest.raises(HTTPException):
        scope_response("issue-review", AGENT_SCOPES["issue-review"], SITE, "nope")


def test_resolve_scope_rejects_unknown_action():
    with pytest.raises(HTTPException) as err:
        resolve_scope("nope")
    assert err.value.status_code == 404
    assert 'Unknown agent action "nope"' in err.value.detail


@pytest.fixture
async def scope_client():
    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def make_site(client):
    r = await client.post(
        "/api/v1/sites", json={"domain": "acmecoffeegear.example", "name": "Acme Coffee Gear"}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_endpoint_serves_the_scope(scope_client, email):
    await signup(scope_client, email)
    site = await make_site(scope_client)

    r = await scope_client.get(
        "/api/v1/agent/scope",
        params={"action": "issue-review"},
        headers={"x-meelu-site": site["id"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["desk"] == "technical-seo"
    assert body["writes"] == [
        "reject_issue",
        "restore_issue",
        "save_note",
        "update_note",
        "delete_note",
    ]
    assert site["id"] in body["systemPrompt"]


async def test_endpoint_accepts_name_as_the_action_alias(scope_client, email):
    await signup(scope_client, email)
    site = await make_site(scope_client)

    r = await scope_client.get(
        "/api/v1/agent/scope", params={"name": "ask-site"}, headers={"x-meelu-site": site["id"]}
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["action"] == "ask-site"
    assert r.json()["data"]["desk"] == "site"


async def test_endpoint_global_scope_needs_no_site(scope_client, email):
    await signup(scope_client, email)

    r = await scope_client.get("/api/v1/agent/scope", params={"action": "profile-setup"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["global"] is True
    assert r.json()["data"]["createToolName"] == "mcp__meelu__save_profile"


async def test_endpoint_requires_a_site_for_site_scopes(scope_client, email):
    await signup(scope_client, email)

    r = await scope_client.get("/api/v1/agent/scope", params={"action": "plan"})
    assert r.status_code == 400


async def test_endpoint_rejects_an_unknown_action(scope_client, email):
    await signup(scope_client, email)

    r = await scope_client.get("/api/v1/agent/scope", params={"action": "nope"})
    assert r.status_code == 404


async def test_endpoint_needs_authentication(scope_client):
    r = await scope_client.get("/api/v1/agent/scope", params={"action": "profile-setup"})
    assert r.status_code == 401
