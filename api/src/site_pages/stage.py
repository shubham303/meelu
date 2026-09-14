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

STAGE_SQL = {
    "pending": "status is null and not blocked_by_robots",
    "blocked": "blocked_by_robots",
    "failed": "status >= 400 or status = 0",
    "skipped": "status = 200 and shallow",
    "crawled": """status = 200 and not shallow and (body_text is null
             or chunked_from_hash is null
             or chunked_from_hash is distinct from content_hash)""",
    "indexed": """status = 200 and not shallow and body_text is not null
             and chunked_from_hash is not distinct from content_hash""",
}

CRAWL_COMPLETE_SQL = f"""(({STAGE_SQL["indexed"]})
      or ({STAGE_SQL["skipped"]})
      or ({STAGE_SQL["blocked"]}))
     and embed_state is distinct from 'failed'"""
