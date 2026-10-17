from src.providers.seo_data.shape import own_domain
from src.seo.serp_history.presence import belongs_to
from src.seo.serp_results.constants import (
    MIN_SIBLING_OVERLAP,
    POISONED_MESSAGE,
    TOP_CHECKED,
    WEAK_PAGE_RANK,
    WEAK_TOP_SUSPECT,
    Verdict,
)
from src.seo.serp_results.schemas import SerpResult, SiblingCheck


def organic(serp: dict | None, top: int) -> list[dict]:
    found: dict[int, dict] = {}
    for item in (serp or {}).get("items") or []:
        if not isinstance(item, dict) or item.get("type") != "organic" or not item.get("url"):
            continue
        rank = item.get("rank_group")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank > top or rank in found:
            continue
        rating = item.get("rating") if isinstance(item.get("rating"), dict) else {}
        price = item.get("price") if isinstance(item.get("price"), dict) else {}
        found[rank] = {
            "position": rank,
            "url": str(item["url"]),
            "domain": own_domain(item.get("domain") or item["url"]),
            "title": item.get("title"),
            "description": item.get("description"),
            "breadcrumb": item.get("breadcrumb"),
            "website_name": item.get("website_name"),
            "highlighted": [h for h in item.get("highlighted") or [] if isinstance(h, str)],
            "date": item.get("timestamp"),
            "rating": number(rating.get("value")),
            "rating_votes": whole(rating.get("votes_count")),
            "price": price.get("displayed_price"),
            "featured_snippet": bool(item.get("is_featured_snippet")),
            "video": bool(item.get("is_video")),
        }
    return [found[k] for k in sorted(found)]


def number(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def is_weak(page_rank: int | None) -> bool:
    return (page_rank or 0) < WEAK_PAGE_RANK


def rank_of(ranks: dict[str, dict], url: str) -> dict:
    return ranks.get(url) or ranks.get(url.rstrip("/")) or ranks.get(f"{url.rstrip('/')}/") or {}


def whole(value) -> int | None:
    return round(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def rated(rows: list[dict], ranks: dict[str, dict], site_domain: str) -> list[SerpResult]:
    site = own_domain(site_domain)
    rated_rows = []
    for row in rows:
        facts = rank_of(ranks, row["url"])
        page_rank, domain_rank = whole(facts.get("rank")), whole(facts.get("main_domain_rank"))
        ours = belongs_to(row["domain"], site)
        rated_rows.append(
            SerpResult(
                **row,
                page_rank=page_rank,
                domain_rank=domain_rank,
                weak=not ours and is_weak(page_rank),
                ours=ours,
            )
        )
    return rated_rows


def sibling_check(keyword: str, main: list[dict], sibling: list[dict]) -> SiblingCheck:
    ours = {r["domain"] for r in main}
    theirs = {r["domain"] for r in sibling}
    shared = len(ours & theirs)
    smaller = min(len(ours), len(theirs))
    return SiblingCheck(
        keyword=keyword,
        shared_domains=shared,
        overlap=round(shared / smaller, 3) if smaller else 0.0,
    )


def verdict(
    results: list[SerpResult], siblings: list[SiblingCheck]
) -> tuple[Verdict, int, float | None, list[str]]:
    top = results[:TOP_CHECKED]
    weak_top = sum(r.weak for r in top)
    reasons: list[str] = []
    weak = weak_top >= WEAK_TOP_SUSPECT
    if weak:
        reasons.append(
            f"{weak_top} of the top {len(top)} results have page rank under {WEAK_PAGE_RANK}, "
            "too weak to hold those spots on merit, whatever their domain."
        )
    overlap = round(sum(s.overlap for s in siblings) / len(siblings), 3) if siblings else None
    split = overlap is not None and overlap < MIN_SIBLING_OVERLAP
    if split:
        reasons.append(
            f"Only {overlap:.0%} of the top domains also rank for "
            f"{', '.join(s.keyword for s in siblings)}, keywords of the same cluster."
        )
    if not results:
        reasons.append("The results page came back with no organic results.")
        return "suspect", weak_top, overlap, reasons
    if (weak and split) or (len(top) == TOP_CHECKED and weak_top == TOP_CHECKED):
        return "poisoned", weak_top, overlap, reasons
    if weak or split:
        return "suspect", weak_top, overlap, reasons
    return "clean", weak_top, overlap, reasons


def message_for(found: Verdict) -> str | None:
    return POISONED_MESSAGE if found == "poisoned" else None
