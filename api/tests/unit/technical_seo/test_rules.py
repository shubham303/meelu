from src.technical_seo.rules.ai_crawlers import (
    crawler_permissions,
    read_crawler_access,
    robots_allows,
)
from src.technical_seo.rules.host_variants import read_host_variants

PROBE_PAYLOAD = {
    "checkedAt": "2026-01-02T03:04:05.000Z",
    "url": "https://example.com/",
    "baseline": {"status": 200, "bytes": 41231},
    "agents": [
        {"agent": "OAI-SearchBot", "status": 200, "bytes": 41231, "verdict": "allowed"},
        {
            "agent": "ChatGPT-User",
            "status": 403,
            "bytes": 512,
            "verdict": "blocked",
            "reason": "was refused with HTTP 403",
        },
        {
            "agent": "Claude-SearchBot",
            "status": None,
            "bytes": None,
            "verdict": "unknown",
            "reason": "could not be reached",
        },
    ],
}

HOST_VARIANTS_PAYLOAD = {
    "checkedAt": "2026-01-02T03:04:05.000Z",
    "preferred": "https://example.com/",
    "sample": "https://example.com/pricing",
    "variants": [
        {
            "kind": "scheme",
            "url": "http://example.com/",
            "target": "https://example.com/",
            "verdict": "redirects",
            "status": 200,
            "hops": 1,
            "finalUrl": "https://example.com/",
            "canonical": "https://example.com/",
        },
        {
            "kind": "host",
            "url": "https://www.example.com/",
            "target": "https://example.com/",
            "verdict": "duplicate",
            "status": 200,
            "hops": 0,
            "finalUrl": "https://www.example.com/",
            "canonical": None,
        },
        {
            "kind": "trailing-slash",
            "url": "https://example.com/pricing/",
            "target": "https://example.com/pricing",
            "verdict": "unknown",
            "status": None,
            "hops": 0,
            "finalUrl": None,
            "canonical": None,
        },
    ],
}


def test_read_crawler_access_normalises_probe_output():
    access = read_crawler_access(PROBE_PAYLOAD)

    assert access == {
        "checkedAt": "2026-01-02T03:04:05.000Z",
        "url": "https://example.com/",
        "baseline": {"status": 200, "bytes": 41231},
        "agents": [
            {"agent": "OAI-SearchBot", "status": 200, "bytes": 41231, "verdict": "allowed"},
            {
                "agent": "ChatGPT-User",
                "status": 403,
                "bytes": 512,
                "verdict": "blocked",
                "reason": "was refused with HTTP 403",
            },
            {
                "agent": "Claude-SearchBot",
                "status": 0,
                "bytes": 0,
                "verdict": "unknown",
                "reason": "could not be reached",
            },
        ],
    }


def test_read_crawler_access_guards():
    assert read_crawler_access(None) is None
    assert read_crawler_access("nope") is None
    assert read_crawler_access([]) is None

    access = read_crawler_access(
        {
            "agents": [
                {"status": 200},
                {"agent": "GPTBot", "verdict": "sideways"},
                None,
            ]
        }
    )
    assert access["url"] == ""
    assert access["baseline"] == {"status": None, "bytes": None}
    assert access["checkedAt"].endswith("Z")
    assert access["agents"] == [
        {"agent": "GPTBot", "status": None, "bytes": None, "verdict": "unknown"}
    ]


def test_read_crawler_access_caps_agents_and_lengths():
    access = read_crawler_access(
        {
            "agents": [{"agent": f"Bot{i}", "verdict": "allowed"} for i in range(40)]
            + [{"agent": "x" * 100, "verdict": "allowed", "reason": "y" * 500}]
        }
    )
    assert len(access["agents"]) == 32

    one = read_crawler_access({"agents": [{"agent": "x" * 100, "reason": "y" * 500}]})
    assert len(one["agents"][0]["agent"]) == 64
    assert len(one["agents"][0]["reason"]) == 200


def test_read_host_variants_normalises_probe_output():
    variants = read_host_variants(HOST_VARIANTS_PAYLOAD)

    assert variants == {
        "checkedAt": "2026-01-02T03:04:05.000Z",
        "preferred": "https://example.com/",
        "sample": "https://example.com/pricing",
        "variants": [
            {
                "kind": "scheme",
                "url": "http://example.com/",
                "target": "https://example.com/",
                "verdict": "redirects",
                "status": 200,
                "hops": 1,
                "finalUrl": "https://example.com/",
                "canonical": "https://example.com/",
            },
            {
                "kind": "host",
                "url": "https://www.example.com/",
                "target": "https://example.com/",
                "verdict": "duplicate",
                "status": 200,
                "hops": 0,
                "finalUrl": "https://www.example.com/",
                "canonical": None,
            },
            {
                "kind": "trailing-slash",
                "url": "https://example.com/pricing/",
                "target": "https://example.com/pricing",
                "verdict": "unknown",
                "status": 0,
                "hops": 0,
                "finalUrl": None,
                "canonical": None,
            },
        ],
    }


def test_read_host_variants_guards():
    assert read_host_variants(None) is None
    assert read_host_variants("nope") is None

    variants = read_host_variants(
        {
            "variants": [
                {"kind": "bogus", "url": "https://example.com/"},
                {"kind": "case", "url": 12},
                {"kind": "case", "url": "https://example.com/A", "verdict": "sideways", "hops": -3},
            ]
        }
    )
    assert variants["preferred"] == ""
    assert variants["sample"] is None
    assert variants["variants"] == [
        {
            "kind": "case",
            "url": "https://example.com/A",
            "target": "",
            "verdict": "unknown",
            "status": None,
            "hops": 0,
            "finalUrl": None,
            "canonical": None,
        }
    ]


def test_read_host_variants_caps_variants():
    variants = read_host_variants(
        {"variants": [{"kind": "host", "url": f"https://h{i}.example.com/"} for i in range(12)]}
    )
    assert len(variants["variants"]) == 8


def test_robots_allows_reads_groups_and_wildcards():
    body = "User-agent: *\nDisallow: /admin\n\nUser-agent: GPTBot\nDisallow: /\n"

    assert robots_allows(body, "Googlebot") is True
    assert robots_allows(body, "Googlebot", "/admin") is False
    assert robots_allows(body, "GPTBot") is False
    assert robots_allows(body, "GPTBot-Image") is False

    allow_wins = "User-agent: *\nDisallow: /\nAllow: /public\n"
    assert robots_allows(allow_wins, "Googlebot", "/public/page") is True
    assert robots_allows(allow_wins, "Googlebot", "/private") is False


def test_crawler_permissions_covers_every_known_agent():
    permissions = crawler_permissions("User-agent: Google-Extended\nDisallow: /\n")
    blocked = [c.agent for c in permissions if not c.allowed]
    assert blocked == ["Google-Extended"]
    assert len(permissions) == 15


def _site(**facts):
    from src.sites.models.site import Site

    return Site(id="site_x", user_id="user_x", domain="example.com", name="Example", **facts)


def _held(rules):
    return {r.kind for r in rules if r.holds}


def test_well_known_rules_read_the_site_record():
    from datetime import UTC, datetime

    from src.technical_seo.rules.well_known import well_known_rules

    now = datetime.now(UTC)

    assert _held(well_known_rules(_site(robots_fetched_at=now, robots_status=404))) == {
        "robots-missing"
    }
    assert _held(well_known_rules(_site(robots_fetched_at=now, robots_status=500))) == {
        "robots-unreadable"
    }

    blocks_assets = _site(
        robots_fetched_at=now,
        robots_status=200,
        robots_txt="User-agent: *\nDisallow: /assets/\nSitemap: https://example.com/sitemap.xml\n",
    )
    assert _held(well_known_rules(blocks_assets)) == {"robots-blocks-assets"}

    no_sitemap_line = _site(
        robots_fetched_at=now, robots_status=200, robots_txt="User-agent: *\nDisallow: /admin\n"
    )
    assert _held(well_known_rules(no_sitemap_line)) == {"robots-no-sitemap"}

    crawled_without_sitemap = _site(last_crawled_at=now, sitemap_url_count=0)
    assert _held(well_known_rules(crawled_without_sitemap)) == {"sitemap-missing"}

    odd_sitemap = _site(
        last_crawled_at=now,
        sitemap_url_count=1,
        sitemap_urls=["https://example.com/sitemap_index.xml"],
        sitemap_at_root=False,
    )
    assert _held(well_known_rules(odd_sitemap)) == {"sitemap-not-at-standard-url"}

    assert _held(well_known_rules(_site(llms_fetched_at=now, llms_status=404))) == {"llms-missing"}
    assert _held(
        well_known_rules(_site(llms_fetched_at=now, llms_status=200, llms_txt="<!doctype html>"))
    ) == {"llms-not-plain-text"}


def test_ai_permission_rules_read_robots_and_edge_probes():
    from datetime import UTC, datetime

    from src.technical_seo.rules.ai_crawlers import ai_permission_rules

    now = datetime.now(UTC)

    googlebot_out = _site(
        robots_fetched_at=now,
        robots_status=200,
        robots_txt="User-agent: Googlebot\nDisallow: /\n",
    )
    assert "googlebot-blocked" in _held(ai_permission_rules(googlebot_out))

    search_out = _site(
        robots_fetched_at=now,
        robots_status=200,
        robots_txt="User-agent: OAI-SearchBot\nDisallow: /\nUser-agent: Claude-User\nDisallow: /\n",
    )
    held = _held(ai_permission_rules(search_out))
    assert "ai-search-crawler-blocked" in held
    assert "ai-user-fetch-blocked" in held
    assert "ai-permissions-inconsistent" in held

    training_out = _site(
        robots_fetched_at=now,
        robots_status=200,
        robots_txt="User-agent: Google-Extended\nDisallow: /\nUser-agent: CCBot\nDisallow: /\n",
    )
    rules = ai_permission_rules(training_out)
    assert _held(rules) == {"ai-training-blocked"}
    training = next(r for r in rules if r.kind == "ai-training-blocked")
    assert "robots.txt disallows Common Crawl's CCBot" in training.issue
    assert "it also sets the training opt-out token Google-Extended to disallow" in training.issue
    assert "Google-Extended in particular is a directive" in training.issue

    edge = _site(
        crawler_access={
            "baseline": {"status": 200, "bytes": 1000},
            "agents": [
                {
                    "agent": "PerplexityBot",
                    "verdict": "blocked",
                    "reason": "was refused with HTTP 403",
                }
            ],
        }
    )
    rules = ai_permission_rules(edge)
    blocked_at_edge = next(r for r in rules if r.kind == "ai-crawler-blocked-at-edge")
    assert blocked_at_edge.holds
    assert "Perplexity's PerplexityBot was refused with HTTP 403" in blocked_at_edge.issue


def test_host_variant_rules_read_the_probe():
    from src.technical_seo.rules.host_variants import host_variant_rules, read_host_variants

    site = _site(host_variants=read_host_variants(HOST_VARIANTS_PAYLOAD))
    assert _held(host_variant_rules(site)) == {"host-variant-duplicate"}

    http_open = _site(
        host_variants={
            "preferred": "https://example.com/",
            "sample": None,
            "variants": [
                {
                    "kind": "scheme",
                    "url": "http://example.com/",
                    "verdict": "duplicate",
                    "hops": 0,
                }
            ],
        }
    )
    assert _held(host_variant_rules(http_open)) == {"http-not-redirected"}

    home_only = _site(
        host_variants={
            "preferred": "https://example.com/",
            "sample": "https://example.com/pricing",
            "variants": [
                {
                    "kind": "host",
                    "url": "https://www.example.com/",
                    "verdict": "redirects",
                    "hops": 1,
                },
                {
                    "kind": "host-path",
                    "url": "https://www.example.com/pricing",
                    "target": "https://example.com/pricing",
                    "verdict": "duplicate",
                    "status": 200,
                    "hops": 0,
                },
            ],
        }
    )
    assert _held(host_variant_rules(home_only)) == {"host-path-not-redirected"}

    chained = _site(
        host_variants={
            "preferred": "https://example.com/",
            "variants": [
                {"kind": "scheme", "url": "http://example.com/", "verdict": "redirects", "hops": 2},
                {
                    "kind": "case",
                    "url": "https://example.com/PRICING",
                    "verdict": "canonicalised",
                    "hops": 0,
                },
            ],
        }
    )
    assert _held(host_variant_rules(chained)) == {
        "host-variant-canonicalised",
        "host-variant-redirect-chain",
    }


def test_rule_set_is_complete_and_kinds_are_known():
    from src.technical_seo.constants import SITE_ISSUE_KINDS
    from src.technical_seo.rules import PAGE_RULES, site_rules
    from src.technical_seo.rules.render import RenderCounts

    NO_RENDERS = RenderCounts(0, 0, 0, 0)

    assert len(PAGE_RULES) == 194
    assert len(site_rules(_site(), NO_RENDERS)) == 25

    for rule in PAGE_RULES:
        assert rule.kind in SITE_ISSUE_KINDS
        assert rule.severity in ("p0", "p1", "p2", "p3")
    for rule in site_rules(_site(), NO_RENDERS):
        assert rule.kind in SITE_ISSUE_KINDS

    kinds = [r.kind for r in PAGE_RULES] + [r.kind for r in site_rules(_site(), NO_RENDERS)]
    assert len(kinds) == len(set(kinds))
    assert set(kinds) == set(SITE_ISSUE_KINDS)
