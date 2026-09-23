import math
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from src.core.schemas import js_iso
from src.sites.schemas import SiteRecord
from src.technical_seo.rules.types import SiteRule

KINDS = {"scheme", "host", "host-path", "trailing-slash", "case"}

VERDICTS = {
    "duplicate",
    "canonicalised",
    "redirects",
    "elsewhere",
    "absent",
    "distinct",
    "unknown",
}

_MISSING = object()


def _text(value: Any, limit: int = 2048) -> str | None:
    return value[:limit] if isinstance(value, str) and value else None


def _count(value: Any) -> int:
    n = _js_number(value)
    return math.floor(n) if n is not None and n > 0 else 0


def _js_number(value: Any) -> float | int | None:
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


def read_host_variants(payload: Any) -> dict[str, Any] | None:
    if not payload or not isinstance(payload, dict):
        return None
    variants = payload.get("variants")
    if not isinstance(variants, list):
        variants = []

    kept = [
        entry
        for entry in (v if isinstance(v, dict) else {} for v in variants)
        if str(entry.get("kind")) in KINDS and isinstance(entry.get("url"), str)
    ][:8]

    def variant_out(entry: dict[str, Any]) -> dict[str, Any]:
        verdict = str(entry.get("verdict"))
        status = _js_number(entry.get("status", _MISSING))
        return {
            "kind": str(entry["kind"]),
            "url": str(entry["url"])[:2048],
            "target": _text(entry.get("target")) or "",
            "verdict": verdict if verdict in VERDICTS else "unknown",
            "status": status,
            "hops": _count(entry.get("hops", _MISSING)),
            "finalUrl": _text(entry.get("finalUrl")),
            "canonical": _text(entry.get("canonical")),
        }

    return {
        "checkedAt": _text(payload.get("checkedAt")) or js_iso(datetime.now(UTC)),
        "preferred": _text(payload.get("preferred")) or "",
        "sample": _text(payload.get("sample")),
        "variants": [variant_out(entry) for entry in kept],
    }


def _www_form(probe: dict[str, Any] | None) -> str:
    try:
        if probe and urlsplit(str(probe.get("url"))).hostname.startswith("www."):
            return "www"
    except Exception:
        return "bare"
    return "bare"


def _listed(probes: list[dict[str, Any]]) -> str:
    return ", ".join(str(v.get("url")) for v in probes)


def _field(probe: dict[str, Any] | None, key: str, default: str) -> Any:
    if probe is None or probe.get(key) is None:
        return default
    return probe[key]


def host_variant_rules(site: SiteRecord) -> list[SiteRule]:
    probed = site.host_variants if isinstance(site.host_variants, dict) else None
    variants = probed.get("variants") if probed else None
    if not isinstance(variants, list):
        variants = []
    variants = [v for v in variants if isinstance(v, dict)]

    def at(kind: str) -> dict[str, Any] | None:
        return next((v for v in variants if v.get("kind") == kind), None)

    scheme = at("scheme")
    host = at("host")
    host_path = at("host-path")
    slash = at("trailing-slash")
    cased = at("case")

    preferred = (probed.get("preferred") if probed else None) or ""
    sample = (probed.get("sample") if probed else None) or ""

    canonicalised = [v for v in variants if v.get("verdict") == "canonicalised"]
    chains = [
        v
        for v in variants
        if v.get("verdict") == "redirects" and _count(v.get("hops", _MISSING)) > 1
    ]

    other = _www_form(host)
    chosen = "bare" if other == "www" else "www"

    host_path_line = (
        f"redirects to {_field(host_path, 'finalUrl', 'somewhere else')} instead of "
        f"{_field(host_path, 'target', 'the matching page')}"
        if host_path is not None and host_path.get("verdict") == "elsewhere"
        else f"answered {_field(host_path, 'status', 'directly')} instead of redirecting to "
        f"{_field(host_path, 'target', 'the matching page')}"
    )

    return [
        SiteRule(
            kind="http-not-redirected",
            severity="p1",
            issue=(
                f"{_field(scheme, 'url', 'The http address')} answered 200 with the same page as {preferred} and "
                "did not redirect, so the whole site exists a second time on an insecure protocol. Every "
                "URL has an http twin; a search engine has to guess which of the two to index, links and "
                "any ranking signal they carry split between them, and anyone who reaches the http copy "
                "browses unencrypted. Redirect every http request to the same path on https with a "
                "single permanent 301 at the server or CDN, and leave the redirect in place — this is "
                "not something a canonical tag can fix, because the insecure copy still has to be "
                "fetched before the tag is read."
            ),
            holds=scheme is not None and scheme.get("verdict") == "duplicate",
        ),
        SiteRule(
            kind="host-variant-duplicate",
            severity="p1",
            issue=(
                f"Both host forms serve the site: {_field(host, 'url', 'the other host')} answered 200 with the "
                f"same page as {preferred}, neither redirects to the other, and the {other} form does "
                "not point a canonical at the other one. That is the whole site duplicated at the host "
                "level — every page has two addresses, and the two accumulate links, crawls and ranking "
                "signals separately. Decide which host is the real one (this crawl started from the "
                f"{chosen} form), then 301 the other to it path for path, not to its home page, and make "
                "every internal link, sitemap entry and canonical tag use the chosen host."
            ),
            holds=host is not None and host.get("verdict") == "duplicate",
        ),
        SiteRule(
            kind="trailing-slash-duplicate",
            severity="p2",
            issue=(
                f"The server treats a trailing slash as a second address: {_field(slash, 'url', 'the slashed form')} "
                f"answered 200 with the same page as {sample} and neither redirects to the other, nor "
                "does the slashed form canonicalise to the unslashed one. Every path on the "
                "site therefore exists twice, and which of the two gets linked is down to whoever wrote "
                "the link. Pick one convention, 301 the other form to it, and use the chosen form "
                "consistently in internal links, the sitemap and canonical tags."
            ),
            holds=slash is not None and slash.get("verdict") == "duplicate",
        ),
        SiteRule(
            kind="case-variant-duplicate",
            severity="p2",
            issue=(
                f"The server is case-insensitive about paths: {_field(cased, 'url', 'an upper-case form')} "
                f"answered 200 with the same page as {sample} instead of a 404, and does not canonicalise "
                "back to the lower-case form. URLs are case-sensitive to search engines even when the "
                "server is relaxed about them, so any mistyped or mis-cased link anywhere on the web "
                "creates a real, indexable duplicate of the page. Either 301 mixed-case requests to the "
                "lower-case path or return 404 for them, and keep every internal link lower-case."
            ),
            holds=cased is not None and cased.get("verdict") == "duplicate",
        ),
        SiteRule(
            kind="host-variant-distinct",
            severity="p2",
            issue=(
                f"{_field(host, 'url', 'The other host form')} answered 200 with different content from "
                f"{preferred}, and does not redirect to it. Those are two separate websites that happen "
                "to share a registered domain, not one site reachable two ways — so this crawl read only "
                f"the {chosen} form and nothing on the {other} form is on record here. That is worth "
                "confirming rather than assuming: the usual causes are a staging or legacy site left "
                "running on the host nobody redirected, or a marketing page parked in front of the real "
                "one. If the two are meant to be the same site, 301 one to the other path for path. If "
                "they are genuinely separate, add the other one as its own website so it gets crawled "
                "and audited on its own terms."
            ),
            holds=host is not None and host.get("verdict") == "distinct",
        ),
        SiteRule(
            kind="host-variant-elsewhere",
            severity="p1",
            issue=(
                f"{_field(host, 'url', 'The other host form')} does redirect, but it lands on "
                f"{_field(host, 'finalUrl', 'somewhere that is not this site')} rather than {preferred}. A "
                "redirect that goes to the wrong place is worse than none: anyone who types the "
                f"{other} form, and every link anywhere on the web that still points at it, is handed "
                "off to an address you did not choose, and whatever equity those links carry goes with "
                f"them. Point the {other} form at {preferred}, path for path, with a single 301."
            ),
            holds=host is not None and host.get("verdict") == "elsewhere",
        ),
        SiteRule(
            kind="host-path-not-redirected",
            severity="p1",
            issue=(
                f"The home page of the {other} host form reaches {preferred}, but a real page on it "
                f"does not: {_field(host_path, 'url', 'the same path on the other host')} "
                + host_path_line
                + ". This is the home-page-only redirect, and it is the most common way a site ends up "
                "indexed twice while looking correctly configured: whoever set it up tested the home "
                "page, saw it redirect, and stopped. Every page except the home page still exists at "
                "two addresses, so Google keeps two records of the site and splits links and ranking "
                "signals between them. The redirect rule has to map the whole path across, not send "
                "everything to the root."
            ),
            holds=(
                host is not None
                and host.get("verdict") == "redirects"
                and host_path is not None
                and host_path.get("verdict") in ("duplicate", "canonicalised", "elsewhere")
            ),
        ),
        SiteRule(
            kind="host-variant-canonicalised",
            severity="p3",
            issue=(
                f"{_listed(canonicalised)} serve{'s' if len(canonicalised) == 1 else ''} the same content "
                "as the preferred address rather than redirecting, but the canonical tag on each one "
                "points at the preferred address, so search engines are told which copy to keep and the "
                "duplication is unlikely to cost anything. It is still worth turning into a 301: a "
                "canonical is a hint that can be ignored, it only works once the duplicate has been "
                "fetched and parsed, and no AI crawler is guaranteed to honour it. Nothing is broken "
                "here — this is the cheap version of a fix that is already mostly done."
            ),
            holds=len(canonicalised) > 0,
        ),
        SiteRule(
            kind="host-variant-redirect-chain",
            severity="p3",
            issue=(
                "Some address variants do reach the preferred address, but through more than one "
                "redirect: "
                + "; ".join(
                    f"{v.get('url')} takes {_count(v.get('hops', _MISSING))} hops" for v in chains
                )
                + ". The destination is right, so nothing is duplicated, but each hop is another request "
                "before anything is read, and chains of this kind grow — the usual cause is one rule "
                "fixing the protocol and a separate rule fixing the host, applied one after the other. "
                "Collapse them into a single 301 that goes straight to the final address."
            ),
            holds=len(chains) > 0,
        ),
    ]
