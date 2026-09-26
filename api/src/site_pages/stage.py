STAGES = ("pending", "blocked", "failed", "skipped", "crawled", "indexed")


def page_stage(
    blocked_by_robots: bool,
    status: int | None,
    shallow: bool,
    content_hash: str | None,
    chunked_from_hash: str | None,
    has_text: bool | None = None,
) -> str:
    if blocked_by_robots:
        return "blocked"
    if status is None:
        return "pending"
    if status >= 400 or status == 0:
        return "failed"
    if shallow:
        return "skipped"
    if has_text is False:
        return "crawled"
    return "indexed" if chunked_from_hash and chunked_from_hash == content_hash else "crawled"


STAGE_LABEL = {
    "pending": "not fetched yet",
    "blocked": "robots.txt disallows it",
    "failed": "the site returned an error",
    "skipped": "not worth reading",
    "crawled": "fetched, not searchable yet",
    "indexed": "searchable",
}

CRAWL_COMPLETE_STAGES = ("indexed", "skipped", "blocked")
