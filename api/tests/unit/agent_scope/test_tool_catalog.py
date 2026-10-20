import re

import src.agent.tools.core
import src.agent_plans.tools
import src.content.tools
import src.data_analytics.tools as analytics_tools
import src.notes.tools
import src.profile.tools
import src.reports.tools
import src.site_pages.tools
import src.technical_seo.tools  # noqa: F401
from src.agent import server
from src.agent_scope.lib import SiteRef
from src.agent_scope.registry import AGENT_SCOPES
from src.agent_scope.service import agent_scope_service
from src.core.orm import Base

SITE = SiteRef(id="site_test_0001", name="Acme", domain="acme.example")
SCRATCHPAD_TOOLS = {
    "what_is_scratchpad",
    "scratchpad_next",
    "scratchpad_claim",
    "scratchpad_update_status",
    "scratchpad_metrics",
    "scratchpad_get_failed",
    "scratchpad_search",
    "scratchpad_info",
    "scratchpad_delete",
}
SHARED_READS = {"run_sql", "find_plans", "get_plan"} | SCRATCHPAD_TOOLS


def catalog() -> dict[str, dict]:
    return {info.name: dict(info.meta or {}) for info in server.mcp._tool_manager.list_tools()}


def allowed_for(desks: set[str], writes: list[str], providers: set[str] = frozenset()) -> set[str]:
    cat = catalog()
    allowed = set(writes)
    for name, meta in cat.items():
        if meta.get("meelu/writes"):
            continue
        provider = meta.get("meelu/provider")
        if provider is not None:
            if provider in providers:
                allowed.add(name)
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
        if "meelu/provider" in meta:
            assert "meelu/desk" not in meta, name
            assert not meta["meelu/writes"], name


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
        if "meelu/desk" not in meta and "meelu/provider" not in meta and not meta["meelu/writes"]
    }
    assert untagged == SHARED_READS


def test_provider_tools_hide_until_the_scope_lists_their_domain():
    body = agent_scope_service.scope_response("ask-pages", AGENT_SCOPES["ask-pages"], SITE)
    assert "seo_ranked_keywords" not in allowed_for({"pages"}, body.writes)
    assert "seo_ranked_keywords" in allowed_for({"pages"}, body.writes, {"seo-data"})


def test_untagged_writes_are_only_the_note_tools():
    untagged = {
        name
        for name, meta in catalog().items()
        if "meelu/desk" not in meta and meta["meelu/writes"]
    }
    assert untagged == {"save_note", "update_note", "delete_note"}


def test_pages_desk_sees_eight_tools():
    body = agent_scope_service.scope_response("ask-pages", AGENT_SCOPES["ask-pages"], SITE)
    allowed = allowed_for({"pages"}, body.writes)
    assert allowed == SHARED_READS | {
        "search_page",
        "set_page_type",
        "save_note",
        "update_note",
        "delete_note",
    }


def test_loading_the_analytics_desk_adds_the_engine():
    body = agent_scope_service.scope_response(
        "ask-pages", AGENT_SCOPES["ask-pages"], SITE, "analytics"
    )
    allowed = allowed_for({"pages", "analytics"}, body.writes)
    assert "cluster" in allowed
    assert "forecast" in allowed
    assert "content_create_piece" not in allowed


def test_the_analytics_chat_has_the_engine_and_report_writes():
    body = agent_scope_service.scope_response("ask-analytics", AGENT_SCOPES["ask-analytics"], SITE)
    allowed = allowed_for({"analytics"}, body.writes)
    assert {"cluster", "forecast", "compare_periods", "run_sql"} <= allowed
    assert {"save_report", "update_report"} <= allowed
    assert body.allow_attachments is False


def test_report_writers_get_the_report_tools():
    for action in ("ask-analytics", "ask-seo", "issue-review"):
        body = agent_scope_service.scope_response(action, AGENT_SCOPES[action], SITE)
        assert {"save_report", "update_report"} <= set(body.writes), action
    body = agent_scope_service.scope_response("ask-pages", AGENT_SCOPES["ask-pages"], SITE)
    assert "save_report" not in body.writes


def test_every_write_in_a_scope_is_a_registered_write():
    cat = catalog()
    for action, scope in AGENT_SCOPES.items():
        body = agent_scope_service.scope_response(action, scope, None if scope.is_global else SITE)
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
        body = agent_scope_service.scope_response(action, scope, None if scope.is_global else SITE)
        allowed = allowed_for({scope.desk, *body.loaded_desks}, body.writes) | {"add_desk"}
        for token in set(TOKEN.findall(body.system_prompt)):
            if token in schema:
                continue
            if token in cat:
                assert token in allowed, f"{action} names {token}, which this desk cannot call"
            else:
                assert not token.startswith("meelu_"), f"{action} names the retired tool {token}"
