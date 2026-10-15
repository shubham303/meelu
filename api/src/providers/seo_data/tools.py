from typing import Literal

from pydantic import BaseModel

from src.agent.context import require_site
from src.agent.server import tool
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data

DOMAIN = "seo-data"


class LlmTarget(BaseModel):
    domain: str | None = None
    keyword: str | None = None


def caller() -> Caller:
    ctx = require_site()
    return Caller(user_id=ctx.user_id, site_id=ctx.site_id)


@tool(provider=DOMAIN)
async def seo_ranked_keywords(
    domain: str,
    limit: int = 100,
    exclude_brand_terms: list[str] | None = None,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """Keywords a domain ranks for. exclude_brand_terms drops keywords containing those
    terms (at most eight)."""
    return await seo_data.ranked_keywords(
        caller(), domain, limit, exclude_brand_terms or [], location_code, language_code
    )


@tool(provider=DOMAIN)
async def seo_trend(
    keywords: list[str], location_code: int | None = None, language_code: str | None = None
) -> dict:
    """Daily interest over time for up to 50 keywords. Five keywords per vendor call."""
    return await seo_data.trend(caller(), keywords, location_code, language_code)


@tool(provider=DOMAIN)
async def seo_relevant_pages(
    domain: str,
    limit: int = 100,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """A domain's pages ordered by organic traffic, with the keyword count each ranks for."""
    return await seo_data.relevant_pages(caller(), domain, limit, location_code, language_code)


@tool(provider=DOMAIN)
async def seo_lighthouse(url: str, strategy: Literal["mobile", "desktop"] = "mobile") -> dict:
    """Run Lighthouse on one URL for mobile or desktop and return the raw report."""
    return await seo_data.lighthouse(caller(), url, strategy)


@tool(provider=DOMAIN)
async def seo_llm_mentions(
    targets: list[LlmTarget],
    platform: Literal["chat_gpt", "google"] = "google",
    limit: int = 300,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """Prompts on an AI platform whose answers mention a domain or keyword (up to ten
    targets), with cited URLs and co-mentioned brands."""
    return await seo_data.llm_mentions(
        caller(),
        [t.model_dump() for t in targets],
        platform,
        limit,
        location_code,
        language_code,
    )
