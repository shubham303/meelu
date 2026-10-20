from uuid import uuid4

import pytest
from sqlalchemy import text

from src.agent.context import AgentContext, set_context
from src.connected_apps import composio
from src.connected_apps.service import connected_app_service
from src.connected_apps.tools import DESK_TOOLS
from src.core.database import unit_of_work
from src.providers.errors import ProviderRequestError
from src.settings import settings
from tests.conftest import signup


class FakeComposio:
    def __init__(self):
        self.accounts: dict[str, dict] = {}
        self.configs: list[dict] = []
        self.created_configs: list[tuple[str, dict]] = []
        self.executed: list[tuple[str, str, str, dict]] = []
        self.deleted: list[str] = []
        self.result: dict = {"successful": True, "data": {"ok": True}}
        self.links = 0
        self.prefix = uuid4().hex[:8]

    def id(self, n):
        return f"ca_{self.prefix}_{n}"

    async def auth_configs(self, toolkit):
        return [c for c in self.configs if c["toolkit"] == toolkit]

    async def create_auth_config(self, toolkit, auth_config):
        self.created_configs.append((toolkit, auth_config))
        config_id = f"ac_{toolkit}"
        self.configs.append(
            {
                "id": config_id,
                "toolkit": toolkit,
                "status": "ENABLED",
                "is_composio_managed": auth_config["type"] == "use_composio_managed_auth",
                "auth_scheme": auth_config.get("authScheme", "OAUTH2"),
            }
        )
        return config_id

    async def create_link(self, auth_config_id, user_id):
        self.links += 1
        account_id = self.id(self.links)
        self.accounts[account_id] = {"id": account_id, "status": "INITIATED", "user": user_id}
        return {
            "redirect_url": f"https://connect.composio.dev/link/{account_id}",
            "expires_at": "2026-10-20T12:00:00Z",
            "connected_account_id": account_id,
        }

    async def connected_accounts(self, account_ids):
        return [self.accounts[a] for a in account_ids if a in self.accounts]

    async def delete_account(self, account_id):
        self.deleted.append(account_id)
        self.accounts.pop(account_id, None)

    async def tools(self, slugs):
        return [
            {
                "slug": s,
                "name": s.title(),
                "description": f"Does {s}",
                "input_parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}, "is_draft": {"type": "boolean"}},
                    "required": ["query", "is_draft"],
                },
            }
            for s in slugs
            if s != "GMAIL_GET_DRAFT"
        ]

    async def execute(self, slug, user_id, account_id, arguments):
        self.executed.append((slug, user_id, account_id, arguments))
        return self.result

    def activate(self, account_id, word_id="gmail_red-castle"):
        self.accounts[account_id].update(status="ACTIVE", word_id=word_id)


@pytest.fixture
def fake(monkeypatch):
    fake = FakeComposio()
    for name in (
        "auth_configs",
        "create_auth_config",
        "create_link",
        "connected_accounts",
        "delete_account",
        "tools",
        "execute",
    ):
        monkeypatch.setattr(composio, name, getattr(fake, name))
    monkeypatch.setattr(settings, "composio_api_key", "test-key")
    connected_app_service._auth_configs.clear()
    connected_app_service._schemas.clear()
    return fake


async def setup_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    async with unit_of_work() as db:
        user_id = (
            await db.execute(text('SELECT id FROM "user" WHERE email = :e'), {"e": email})
        ).scalar_one()
    return user_id, site


@pytest.fixture
def as_agent():
    def enter(user_id, site_id):
        set_context(
            AgentContext(
                user_id=user_id,
                site_id=site_id,
                site_domain="example.com",
                site_status="active",
                role="r",
                schema="s",
                api_key="k",
            )
        )

    return enter


async def test_connect_then_list_actions(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    email_tools = DESK_TOOLS["email"]

    link = await email_tools["connect"]("gmail")
    assert link.url.startswith("https://connect.composio.dev/link/")
    assert fake.created_configs == [("gmail", {"type": "use_composio_managed_auth"})]
    assert fake.accounts[fake.id(1)]["user"] == f"{user_id}.{site['id']}"

    apps = {a.app: a for a in await email_tools["apps"]()}
    assert apps["gmail"].connections[0].status == "INITIATED"
    assert apps["gmail"].actions == []
    assert apps["outlook"].connections == []

    fake.activate(fake.id(1))
    apps = {a.app: a for a in await email_tools["apps"]()}
    gmail = apps["gmail"]
    assert gmail.connections[0].status == "ACTIVE"
    assert gmail.connections[0].label == "gmail_red-castle"
    by_action = {a.action: a for a in gmail.actions}
    assert "GMAIL_GET_DRAFT" not in by_action
    assert by_action["GMAIL_FETCH_EMAILS"].kind == "read"
    assert by_action["GMAIL_CREATE_EMAIL_DRAFT"].kind == "write"
    assert "GMAIL_SEND_EMAIL" not in by_action

    await email_tools["connect"]("outlook")
    assert len(fake.created_configs) == 2


async def test_api_key_apps_get_a_custom_auth_config(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    await DESK_TOOLS["cms"]["connect"]("webflow")
    assert fake.created_configs == [
        ("webflow", {"type": "use_custom_auth", "authScheme": "API_KEY", "credentials": {}})
    ]
    connected_app_service._auth_configs.clear()
    await DESK_TOOLS["cms"]["connect"]("webflow")
    assert len(fake.created_configs) == 1


async def test_actions_are_bound_to_desk_kind_and_connection(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    cms = DESK_TOOLS["cms"]

    with pytest.raises(ValueError, match="not a CMS app"):
        await cms["connect"]("gmail")
    with pytest.raises(ValueError, match="No active Webflow connection"):
        await cms["read"]("WEBFLOW_LIST_COLLECTIONS", {})

    link = await cms["connect"]("webflow")
    fake.activate(fake.id(1), "webflow_blue-sky")

    with pytest.raises(ValueError, match="not a CMS action"):
        await cms["read"]("WEBFLOW_PUBLISH_SITE", {})
    with pytest.raises(ValueError, match="not a CMS action"):
        await cms["write"]("GMAIL_CREATE_EMAIL_DRAFT", {})
    with pytest.raises(ValueError, match="is a write action"):
        await cms["read"]("WEBFLOW_CREATE_COLLECTION_ITEM", {})
    with pytest.raises(ValueError, match="is a read action"):
        await cms["write"]("WEBFLOW_LIST_COLLECTIONS", {})

    with pytest.raises(ValueError, match="is_draft is set by Meelu"):
        await cms["write"]("WEBFLOW_CREATE_COLLECTION_ITEM", {"query": "c1", "is_draft": False})
    with pytest.raises(ValueError, match="isDraft is set by Meelu"):
        await cms["write"]("WEBFLOW_CREATE_COLLECTION_ITEM", {"query": "c1", "isDraft": False})
    with pytest.raises(ValueError, match="takes no publish"):
        await cms["write"]("WEBFLOW_CREATE_COLLECTION_ITEM", {"query": "c1", "publish": True})
    assert fake.executed == []

    result = await cms["write"]("WEBFLOW_CREATE_COLLECTION_ITEM", {"query": "c1"})
    assert result.connection_id == link.connection_id
    slug, composio_user, account, arguments = fake.executed[-1]
    assert (slug, composio_user, account) == (
        "WEBFLOW_CREATE_COLLECTION_ITEM",
        f"{user_id}.{site['id']}",
        fake.id(1),
    )
    assert arguments == {"query": "c1", "is_draft": True}

    apps = {a.app: a for a in await cms["apps"]()}
    create = next(
        a for a in apps["webflow"].actions if a.action == "WEBFLOW_CREATE_COLLECTION_ITEM"
    )
    assert "is_draft" not in create.input_schema["properties"]
    assert create.input_schema["required"] == ["query"]

    await cms["connect"]("webflow")
    fake.activate(fake.id(2), "webflow_green-leaf")
    await cms["apps"]()
    with pytest.raises(ValueError, match="Several Webflow connections"):
        await cms["read"]("WEBFLOW_LIST_COLLECTIONS", {})
    with pytest.raises(ValueError, match="not an active Webflow connection"):
        await cms["read"]("WEBFLOW_LIST_COLLECTIONS", {}, "capp_nope")


async def test_a_read_right_after_sign_in_finds_the_connection(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    link = await DESK_TOOLS["email"]["connect"]("gmail")
    fake.activate(fake.id(1))
    result = await DESK_TOOLS["email"]["read"]("GMAIL_FETCH_EMAILS", {"query": "is:unread"})
    assert result.connection_id == link.connection_id


async def test_an_active_connection_composio_no_longer_lists_is_removed(
    client, email, fake, as_agent
):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    await DESK_TOOLS["crm"]["connect"]("hubspot")
    fake.activate(fake.id(1))
    await DESK_TOOLS["crm"]["apps"]()
    fake.accounts.pop(fake.id(1))
    apps = {a.app: a for a in await DESK_TOOLS["crm"]["apps"]()}
    assert apps["hubspot"].connections == []
    assert fake.deleted == [fake.id(1)]


async def test_another_site_cannot_use_a_connection(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]
    as_agent(user_id, site["id"])
    link = await DESK_TOOLS["crm"]["connect"]("hubspot")
    fake.activate(fake.id(1), "hubspot_one")
    await DESK_TOOLS["crm"]["apps"]()

    as_agent(user_id, other["id"])
    with pytest.raises(ValueError, match="No active HubSpot connection"):
        await DESK_TOOLS["crm"]["read"]("HUBSPOT_SEARCH_CONTACTS_BY_CRITERIA", {})
    with pytest.raises(ValueError, match="No connection"):
        await DESK_TOOLS["crm"]["disconnect"](link.connection_id)
    assert all(a.connections == [] for a in await DESK_TOOLS["crm"]["apps"]())


async def test_vendor_failures_and_oversized_results(client, email, fake, as_agent, monkeypatch):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    crm = DESK_TOOLS["crm"]
    await crm["connect"]("attio")
    fake.activate(fake.id(1), "attio_one")
    await crm["apps"]()

    fake.result = {"successful": False, "error": "Missing scope", "data": {}}
    with pytest.raises(ValueError, match="Attio refused ATTIO_SEARCH_RECORDS: Missing scope"):
        await crm["read"]("ATTIO_SEARCH_RECORDS", {"query": "acme"})

    fake.result = {"successful": True, "data": {"rows": ["x" * 70_000]}}
    with pytest.raises(ValueError, match="Narrow it"):
        await crm["read"]("ATTIO_SEARCH_RECORDS", {"query": "acme"})

    async def refuse(*args):
        raise ProviderRequestError("composio", 400, "Invalid argument query")

    monkeypatch.setattr(composio, "execute", refuse)
    with pytest.raises(ValueError, match="Attio refused ATTIO_SEARCH_RECORDS: Invalid argument"):
        await crm["read"]("ATTIO_SEARCH_RECORDS", {"query": "acme"})


async def test_disconnect_and_rest_routes(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    as_agent(user_id, site["id"])
    first = await DESK_TOOLS["email"]["connect"]("gmail")
    second = await DESK_TOOLS["crm"]["connect"]("pipedrive")
    headers = {"x-meelu-site": site["id"]}

    r = await client.get("/api/v1/connected-apps", headers=headers)
    assert r.status_code == 200, r.text
    listed = r.json()["data"]
    assert [(a["desk"], a["app"]) for a in listed][:2] == [("email", "gmail"), ("email", "outlook")]
    by_app = {a["app"]: a for a in listed}
    assert by_app["gmail"]["connections"][0]["status"] == "INITIATED"
    assert by_app["pipedrive"]["connections"][0]["connectionId"] == second.connection_id
    assert by_app["hubspot"]["connections"] == []

    fake.activate(fake.id(2), "pipedrive_one")
    r = await client.get("/api/v1/connected-apps", headers=headers)
    pipedrive = {a["app"]: a for a in r.json()["data"]}["pipedrive"]["connections"][0]
    assert (pipedrive["status"], pipedrive["label"]) == ("ACTIVE", "pipedrive_one")

    r = await client.post(
        "/api/v1/connected-apps", json={"desk": "cms", "app": "webflow"}, headers=headers
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["url"].startswith("https://connect.composio.dev/link/")
    r = await client.post(
        "/api/v1/connected-apps", json={"desk": "cms", "app": "gmail"}, headers=headers
    )
    assert r.status_code == 400
    r = await client.post(
        "/api/v1/connected-apps", json={"desk": "nope", "app": "gmail"}, headers=headers
    )
    assert r.status_code == 400

    with pytest.raises(ValueError, match="No connection"):
        await DESK_TOOLS["crm"]["disconnect"](first.connection_id)
    gone = await DESK_TOOLS["email"]["disconnect"](first.connection_id)
    assert gone.id == first.connection_id
    assert fake.deleted == [fake.id(1)]

    r = await client.delete(f"/api/v1/connected-apps/{second.connection_id}", headers=headers)
    assert r.status_code == 200, r.text
    assert fake.deleted == [fake.id(1), fake.id(2)]
    r = await client.delete(f"/api/v1/connected-apps/{second.connection_id}", headers=headers)
    assert r.status_code == 404


async def test_sweep_removes_deleted_sites_and_abandoned_links(client, email, fake, as_agent):
    user_id, site = await setup_site(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]
    as_agent(user_id, site["id"])
    kept = await DESK_TOOLS["email"]["connect"]("gmail")
    fake.activate(fake.id(1))
    await DESK_TOOLS["email"]["apps"]()
    abandoned = await DESK_TOOLS["email"]["connect"]("outlook")
    finished_late = await DESK_TOOLS["crm"]["connect"]("attio")
    fake.activate(fake.id(3))
    as_agent(user_id, other["id"])
    await DESK_TOOLS["cms"]["connect"]("contentful")
    fake.activate(fake.id(4))
    await DESK_TOOLS["cms"]["apps"]()

    async with unit_of_work() as db:
        await db.execute(
            text(
                "UPDATE connected_app SET updated_at = now() - interval '2 days' "
                "WHERE id IN (:a, :b)"
            ),
            {"a": abandoned.connection_id, "b": finished_late.connection_id},
        )
    r = await client.delete(f"/api/v1/sites/{other['id']}")
    assert r.status_code == 200, r.text

    async with unit_of_work() as db:
        assert await connected_app_service.sweep(db) == 2
    assert sorted(fake.deleted) == sorted([fake.id(2), fake.id(4)])
    async with unit_of_work() as db:
        rows = await connected_app_service.list_connections(db, user_id, site["id"])
    assert {(r.id, r.status) for r in rows} == {
        (kept.connection_id, "ACTIVE"),
        (finished_late.connection_id, "ACTIVE"),
    }


async def test_unconfigured_server_says_so(client, email, as_agent, monkeypatch):
    user_id, site = await setup_site(client, email)
    monkeypatch.setattr(settings, "composio_api_key", "")
    connected_app_service._auth_configs.clear()
    as_agent(user_id, site["id"])
    with pytest.raises(ValueError, match="not set up on this server"):
        await DESK_TOOLS["email"]["connect"]("gmail")
