import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.core.schemas import js_iso
from src.sites.schemas import SiteRecord
from src.technical_seo.rules.types import SiteRule

GOOGLEBOT = "Googlebot"


@dataclass(frozen=True)
class AiCrawler:
    operator: str
    job: str
    agent: str
    directive_only: bool


AI_CRAWLERS: list[AiCrawler] = [
    AiCrawler("OpenAI", "training", "GPTBot", False),
    AiCrawler("OpenAI", "search", "OAI-SearchBot", False),
    AiCrawler("OpenAI", "fetch", "ChatGPT-User", False),
    AiCrawler("Anthropic", "training", "ClaudeBot", False),
    AiCrawler("Anthropic", "search", "Claude-SearchBot", False),
    AiCrawler("Anthropic", "fetch", "Claude-User", False),
    AiCrawler("Google", "training", "Google-Extended", True),
    AiCrawler("Perplexity", "search", "PerplexityBot", False),
    AiCrawler("Perplexity", "fetch", "Perplexity-User", False),
    AiCrawler("Apple", "training", "Applebot-Extended", True),
    AiCrawler("Apple", "search", "Applebot", False),
    AiCrawler("Meta", "training", "Meta-ExternalAgent", False),
    AiCrawler("Amazon", "search", "Amazonbot", False),
    AiCrawler("Common Crawl", "training", "CCBot", False),
    AiCrawler("ByteDance", "training", "Bytespider", False),
]


@dataclass
class RobotsRule:
    allow: bool
    pattern: str


@dataclass
class RobotsGroup:
    agents: list[str]
    rules: list[RobotsRule]


def parse_robots(text: str) -> list[RobotsGroup]:
    groups: list[RobotsGroup] = []
    current: RobotsGroup | None = None

    for raw in re.split(r"\r?\n", text):
        line = raw.split("#")[0].strip()
        colon = line.find(":")
        if colon < 0:
            continue
        field = line[:colon].strip().lower()
        value = line[colon + 1 :].strip()

        if field == "user-agent":
            if current is None or current.rules:
                current = RobotsGroup(agents=[], rules=[])
                groups.append(current)
            if value:
                current.agents.append(value.lower())
            continue
        if field not in ("allow", "disallow"):
            continue
        if current is None:
            continue
        current.rules.append(RobotsRule(allow=field == "allow", pattern=value))

    return groups


def rules_for(groups: list[RobotsGroup], agent: str) -> list[RobotsRule]:
    needle = agent.lower()
    best = 0
    for group in groups:
        for named_agent in group.agents:
            if named_agent != "*" and needle.startswith(named_agent) and len(named_agent) > best:
                best = len(named_agent)

    def matches(named_agent: str) -> bool:
        if best == 0:
            return named_agent == "*"
        return len(named_agent) == best and needle.startswith(named_agent)

    return [rule for g in groups if any(matches(a) for a in g.agents) for rule in g.rules]


def path_matcher(pattern: str) -> re.Pattern[str]:
    anchored = pattern.endswith("$")
    body = pattern[:-1] if anchored else pattern
    escaped = "".join(
        ".*" if ch == "*" else f"\\{ch}" if ch in ".+?^${}()|[]\\" else ch for ch in body
    )
    return re.compile(f"^{escaped}{'$' if anchored else ''}")


def robots_allows(robots_txt: str, agent: str, path: str = "/") -> bool:
    rules = rules_for(parse_robots(robots_txt), agent)
    strongest = -1
    allowed = True

    for rule in rules:
        if not rule.pattern:
            continue
        if not path_matcher(rule.pattern).match(path):
            continue
        weight = len(rule.pattern)
        if weight > strongest or (weight == strongest and rule.allow):
            strongest = weight
            allowed = rule.allow

    return True if strongest == -1 else allowed


@dataclass(frozen=True)
class CrawlerPermission(AiCrawler):
    allowed: bool


def crawler_permissions(robots_txt: str, path: str = "/") -> list[CrawlerPermission]:
    return [
        CrawlerPermission(
            c.operator, c.job, c.agent, c.directive_only, robots_allows(robots_txt, c.agent, path)
        )
        for c in AI_CRAWLERS
    ]


EDGE_VERDICTS = {"allowed", "blocked", "unknown"}

_MISSING = object()


def _number_or_null(value: Any) -> float | int | None:
    if value is _MISSING:
        return None
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    if isinstance(value, str):
        raw = value.strip()
        if raw == "":
            return 0
        try:
            n = float(raw)
        except ValueError:
            return None
        if not math.isfinite(n):
            return None
        return int(n) if n.is_integer() else n
    return None


def read_crawler_access(payload: Any) -> dict[str, Any] | None:
    if not payload or not isinstance(payload, dict):
        return None
    baseline = payload.get("baseline") or {}
    if not isinstance(baseline, dict):
        baseline = {}
    agents = payload.get("agents")
    if not isinstance(agents, list):
        agents = []

    checked_at = payload.get("checkedAt")
    url = payload.get("url")

    out_agents = []
    for entry in agents:
        entry = entry if isinstance(entry, dict) else {}
        if not isinstance(entry.get("agent"), str):
            continue
        out_agents.append(entry)
    out_agents = out_agents[:32]

    def agent_out(entry: dict[str, Any]) -> dict[str, Any]:
        verdict = str(entry.get("verdict"))
        out: dict[str, Any] = {
            "agent": str(entry["agent"])[:64],
            "status": _number_or_null(entry.get("status", _MISSING)),
            "bytes": _number_or_null(entry.get("bytes", _MISSING)),
            "verdict": verdict if verdict in EDGE_VERDICTS else "unknown",
        }
        if isinstance(entry.get("reason"), str):
            out["reason"] = entry["reason"][:200]
        return out

    return {
        "checkedAt": checked_at if isinstance(checked_at, str) else js_iso(datetime.now(UTC)),
        "url": url if isinstance(url, str) else "",
        "baseline": {
            "status": _number_or_null(baseline.get("status", _MISSING)),
            "bytes": _number_or_null(baseline.get("bytes", _MISSING)),
        },
        "agents": [agent_out(entry) for entry in out_agents],
    }


@dataclass(frozen=True)
class EdgeBlock:
    agent: str
    operator: str
    job: str
    status: Any
    reason: str


def named(items: list[str]) -> str:
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"


def owned(crawlers: list[Any]) -> str:
    return named([f"{c.operator}'s {c.agent}" for c in crawlers])


def edge_blocks(access: Any) -> list[EdgeBlock]:
    if not isinstance(access, dict):
        return []
    baseline = access.get("baseline") or {}
    if not isinstance(baseline, dict) or baseline.get("status") != 200:
        return []
    agents = access.get("agents")
    if not isinstance(agents, list):
        return []

    blocks: list[EdgeBlock] = []
    for probe in agents:
        if not isinstance(probe, dict) or probe.get("verdict") != "blocked":
            continue
        known = next((c for c in AI_CRAWLERS if c.agent == probe.get("agent")), None)
        blocks.append(
            EdgeBlock(
                agent=str(probe.get("agent")),
                operator=known.operator if known else "an AI operator",
                job=known.job if known else "search",
                status=probe.get("status"),
                reason=probe.get("reason") or "the page came back different",
            )
        )
    return blocks


def ai_permission_rules(site: SiteRecord) -> list[SiteRule]:
    readable = site.robots_fetched_at is not None and site.robots_status == 200
    body = site.robots_txt or ""
    permissions = crawler_permissions(body) if readable else []

    blocked = [c for c in permissions if not c.allowed]
    search_blocked = [c for c in blocked if c.job == "search"]
    fetch_blocked = [c for c in blocked if c.job == "fetch"]
    training_crawlers_blocked = [c for c in blocked if c.job == "training" and not c.directive_only]
    training_tokens_set = [c for c in blocked if c.job == "training" and c.directive_only]
    training_blocked = [*training_crawlers_blocked, *training_tokens_set]

    mismatched = [
        c
        for c in search_blocked
        if any(t.operator == c.operator and t.job == "training" and t.allowed for t in permissions)
    ]

    edge = edge_blocks(site.crawler_access)

    training_parts = []
    if training_crawlers_blocked:
        training_parts.append(f"robots.txt disallows {owned(training_crawlers_blocked)}")
    if training_tokens_set:
        lead = "it also sets" if training_crawlers_blocked else "robots.txt sets"
        token_word = "token" if len(training_tokens_set) == 1 else "tokens"
        training_parts.append(
            f"{lead} the training opt-out {token_word} "
            f"{named([c.agent for c in training_tokens_set])} to disallow"
        )
    training_line = ", and ".join(training_parts)

    google_extended_note = (
        " Google-Extended in particular is a directive rather than a crawler: it governs "
        "training and grounding only and changes nothing about how the site is crawled, "
        "indexed or ranked."
        if any(c.agent == "Google-Extended" for c in training_tokens_set)
        else ""
    )

    mismatch_line = "; ".join(
        f"{c.operator} is still free to take the content for training, while {c.agent} — "
        f"the crawler that puts it into {c.operator}'s answers — is disallowed"
        for c in mismatched
    )

    edge_line = "; ".join(f"{e.operator}'s {e.agent} {e.reason}" for e in edge)

    return [
        SiteRule(
            kind="googlebot-blocked",
            severity="p0",
            issue=(
                "robots.txt disallows Googlebot from the home page. Classic search results and Google's "
                "AI answers are both assembled from the same crawl, so this single rule takes the site "
                "out of both at once, and nothing else in this audit can change that while it stands. "
                "The rule will be in the group for Googlebot or in the one for *; remove it there."
            ),
            holds=readable and not robots_allows(body, GOOGLEBOT),
        ),
        SiteRule(
            kind="ai-search-crawler-blocked",
            severity="p1",
            issue=(
                "robots.txt disallows the crawlers that build the indexes AI assistants answer from: "
                f"{owned(search_blocked)}. Those crawlers are the only route into an answer, so while "
                "these rules stand the site cannot be cited by the assistants that read them at all. "
                "This is a separate decision from model training and blocking it wins nothing back — if "
                "the intent was to stay out of training data, disallow the training crawlers and leave "
                "these allowed."
            ),
            holds=len(search_blocked) > 0,
        ),
        SiteRule(
            kind="ai-user-fetch-blocked",
            severity="p1",
            issue=(
                "robots.txt disallows the agents that fetch a page live when someone asks about it: "
                f"{owned(fetch_blocked)}. These build no index and keep no copy; they run only after a "
                "person has already asked the assistant about this site, and what they fetch is what the "
                "live citation is made of. Blocked, the assistant answers from whatever it happened to "
                "have, or tells the user it could not reach the site."
            ),
            holds=len(fetch_blocked) > 0,
        ),
        SiteRule(
            kind="ai-training-blocked",
            severity="p3",
            issue=(
                f"This site opts out of AI training: {training_line}. That is recorded so the permissions "
                "read as a whole, not because anything is wrong — declining to be training data is a "
                "normal decision and it costs nothing in search rankings or in AI answers. There is "
                "nothing to fix here."
                + google_extended_note
                + " The permissions that do cost visibility are the search and live-fetch ones, and those "
                "are checked separately."
            ),
            holds=len(training_blocked) > 0,
        ),
        SiteRule(
            kind="ai-permissions-inconsistent",
            severity="p1",
            issue=(
                "robots.txt draws the AI line in the wrong place. "
                + mismatch_line
                + ". That blocks the half that costs nothing to allow and allows the half that gives the "
                "most away. Whichever way the decision is meant to go, it almost always wants to be the "
                "other way round: search and live-fetch allowed, training disallowed."
            ),
            holds=len(mismatched) > 0,
        ),
        SiteRule(
            kind="ai-crawler-blocked-at-edge",
            severity="p1",
            issue=(
                "The home page was requested once under each AI crawler's own name and the server, or "
                "the CDN in front of it, turned some of them away: "
                f"{edge_line}. No robots.txt "
                "rule says this, so reading one will never find it — the block sits at the edge, and it "
                "is most often a hosting or bot-protection default that nobody chose. The effect is the "
                "same as a Disallow and it applies whatever robots.txt allows. Check the bot rules on "
                "the CDN or host."
            ),
            holds=len(edge) > 0,
        ),
    ]
