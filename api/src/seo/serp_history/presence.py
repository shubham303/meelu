from collections import Counter
from datetime import date

from src.providers.seo_data.shape import own_domain
from src.seo.serp_history.schemas import DomainPresence


def snapshot_day(snapshot: dict) -> date | None:
    raw = snapshot.get("datetime")
    if not isinstance(raw, str) or len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def belongs_to(domain: str, site_domain: str) -> bool:
    return domain == site_domain or domain.endswith(f".{site_domain}")


def best_by_domain(snapshot: dict, top: int) -> dict[str, tuple[int, str]]:
    best: dict[str, tuple[int, str]] = {}
    for item in snapshot.get("items") or []:
        if not isinstance(item, dict) or item.get("type") != "organic" or not item.get("url"):
            continue
        rank = item.get("rank_group")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank > top:
            continue
        domain = own_domain(item.get("domain") or item["url"])
        if domain and (domain not in best or rank < best[domain][0]):
            best[domain] = (rank, str(item["url"]))
    return best


def by_key(found: dict[str, tuple[int, str]], site: str) -> dict[str, tuple[int, str]]:
    keyed: dict[str, tuple[int, str]] = {}
    for domain, (rank, url) in found.items():
        key = site if belongs_to(domain, site) else domain
        if key not in keyed or rank < keyed[key][0]:
            keyed[key] = (rank, url)
    return keyed


def presence(
    snapshots: list[dict], site_domain: str, top: int, share: float, saved: set[str]
) -> tuple[list[DomainPresence], int, DomainPresence | None]:
    site = own_domain(site_domain)
    per_snapshot = [best_by_domain(s, top) for s in snapshots]
    total = len(per_snapshot)
    if total == 0:
        return [], 0, None

    keyed = [by_key(found, site) for found in per_snapshot]
    ranks: dict[str, list[int]] = {}
    urls: dict[str, Counter[str]] = {}
    for found in keyed:
        for domain, (rank, url) in found.items():
            ranks.setdefault(domain, []).append(rank)
            urls.setdefault(domain, Counter())[url] += 1
    latest = keyed[-1]

    def row(domain: str) -> DomainPresence:
        seen = ranks[domain]
        return DomainPresence(
            domain=domain,
            appearances=len(seen),
            presence=round(len(seen) / total, 3),
            best_position=min(seen),
            average_position=round(sum(seen) / len(seen), 1),
            latest_position=latest[domain][0] if domain in latest else None,
            top_url=urls[domain].most_common(1)[0][0],
            saved=domain in saved,
        )

    rivals = [row(d) for d in ranks if d != site]
    consistent = sorted(
        (r for r in rivals if r.presence >= share),
        key=lambda r: (-r.appearances, r.average_position, r.domain),
    )
    ours = row(site) if site in ranks else None
    return consistent, len(rivals) - len(consistent), ours
