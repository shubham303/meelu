import re

import src.agent.tools.core
import src.agent_plans.tools
import src.content.tools
import src.data_analytics.tools as analytics_tools
import src.notes.tools
import src.profile.tools
import src.site_pages.tools
import src.technical_seo.tools  # noqa: F401
from src.agent import server
from src.agent_scope.lib import SiteRef
from src.agent_scope.registry import AGENT_SCOPES
from src.agent_scope.service import scope_response
from src.core.orm import Base

SITE = SiteRef(id="site_test_0001", name="Acme", domain="acme.example")
SHARED_READS = {"run_sql", "find_plans", "get_plan"}
PENDING_TOOL_NAMES = {
    "outreach_get_project",
    "outreach_list_conversation",
    "outreach_list_prospects",
    "outreach_get_prospect",
    "outreach_update_prospect",
    "outreach_update_project",
    "outreach_send_email",
    "outreach_create_campaign",
    "outreach_start_campaign",
    "analytics_update_session",
    "analytics_add_source",
    "analytics_save_report",
    "analytics_update_report",
    "draw_diagram",
    "draw_dashboard",
    "list_diagram_types",
}


def catalog() -> dict[str, dict]:
    return {info.name: dict(info.meta or {}) for info in server.mcp._tool_manager.list_tools()}


def allowed_for(desks: set[str], writes: list[str]) -> set[str]:
    cat = catalog()
    allowed = set(writes)
    for name, meta in cat.items():
        if meta.get("meelu/writes"):
            continue
        desk = meta.get("meelu/desk")
        if desk is None or desk in desks:
            allowed.add(name)
    return allowed


def test_every_tool_carries_meta_tags():
    for name, meta in catalog().items():
        assert "meelu/writes" in meta, name
        assert isinstance(meta["meelu/writes"], bool), name
        if "meelu/desk" in meta:
            assert isinstance(meta["meelu/desk"], str) and meta["meelu/desk"], name


def test_all_engine_tools_belong_to_the_analytics_desk():
    engine = {
        fn.__name__
        for fn in server.READ_TOOLS | server.WRITE_TOOLS
        if fn.__module__ == analytics_tools.__name__
    }
    assert len(engine) >= 30
    for fn, desk in server.TOOL_DESKS.items():
        if fn.__name__ in engine:
            assert desk == "analytics", fn.__name__
    assert engine <= {fn.__name__ for fn in server.TOOL_DESKS}


def test_only_the_shared_reads_are_untagged():
    untagged = {
        name
        for name, meta in catalog().items()
        if "meelu/desk" not in meta and not meta["meelu/writes"]
    }
    assert untagged == SHARED_READS


def test_untagged_writes_are_only_the_note_tools():
    untagged = {
        name
        for name, meta in catalog().items()
        if "meelu/desk" not in meta and meta["meelu/writes"]
    }
    assert untagged == {"save_note", "update_note", "delete_note"}


def test_pages_desk_sees_seven_tools():
    body = scope_response("ask-pages", AGENT_SCOPES["ask-pages"], SITE)
    allowed = allowed_for({"pages"}, body.writes)
    assert allowed == SHARED_READS | {"search_page", "save_note", "update_note", "delete_note"}


def test_loading_the_analytics_desk_adds_the_engine():
    body = scope_response("ask-pages", AGENT_SCOPES["ask-pages"], SITE, "analytics")
    allowed = allowed_for({"pages", "analytics"}, body.writes)
    assert "cluster" in allowed
    assert "forecast" in allowed
    assert "content_create_piece" not in allowed


def test_every_write_in_a_scope_is_a_registered_write():
    cat = catalog()
    for action, scope in AGENT_SCOPES.items():
        body = scope_response(action, scope, None if scope.is_global else SITE)
        for w in body.writes:
            assert w in cat, (action, w)
            assert cat[w]["meelu/writes"] is True, (action, w)


def schema_words() -> set[str]:
    words = set()
    for table in Base.metadata.tables.values():
        words.add(table.name)
        words.update(c.name for c in table.columns)
    return words


TOKEN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def test_prompts_name_only_tools_the_desk_can_call():
    cat = catalog()
    schema = schema_words()
    for action, scope in AGENT_SCOPES.items():
        body = scope_response(action, scope, None if scope.is_global else SITE)
        external = {t for tpl in body.mcp_servers.values() for t in (tpl.get("tools") or [])}
        allowed = allowed_for({scope.desk}, body.writes) | external | {"add_desk"}
        for token in set(TOKEN.findall(body.system_prompt)):
            if token in schema or token in PENDING_TOOL_NAMES:
                continue
            if token in cat:
                assert token in allowed, f"{action} names {token}, which this desk cannot call"
            else:
                assert not token.startswith("meelu_"), f"{action} names the retired tool {token}"
