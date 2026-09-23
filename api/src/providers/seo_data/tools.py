from typing import Literal

from pydantic import BaseModel

from src.agent.context import current
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data

DOMAIN = "seo-data"


class LlmTarget(BaseModel):
    domain: str | None = None
    keyword: str | None = None


def caller() -> Caller:
    ctx = current()
    return Caller(user_id=ctx.user_id, site_id=ctx.site_id)


@tool(provider=DOMAIN)
async def seo_keyword_facts(
    keywords: list[str], location_code: int | None = None, language_code: str | None = None
) -> dict:
    """Search volume, difficulty, cpc and intent for keywords. Charges credits per vendor
    call; cached results are free."""
    async with unit_of_work() as db:
        return await seo_data.keyword_facts(db, caller(), keywords, location_code, language_code)


@tool(provider=DOMAIN)
async def seo_keyword_ideas(
    seeds: list[str],
    limit: int = 200,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """Keyword ideas grown from seed keywords, with volume, difficulty and intent."""
    async with unit_of_work() as db:
        return await seo_data.keyword_ideas(
            db, caller(), seeds, limit, location_code, language_code
        )


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
    async with unit_of_work() as db:
        return await seo_data.ranked_keywords(
            db, caller(), domain, limit, exclude_brand_terms or [], location_code, language_code
        )


@tool(provider=DOMAIN)
async def seo_rival_domains(
    domain: str, limit: int = 10, location_code: int | None = None, language_code: str | None = None
) -> dict:
    """Domains ranking for the same keywords as the given domain, with intersections and
    average position."""
    async with unit_of_work() as db:
        return await seo_data.rival_domains(
            db, caller(), domain, limit, location_code, language_code
        )


@tool(provider=DOMAIN)
async def seo_serp_snapshot(
    keyword: str,
    device: Literal["desktop", "mobile"] = "desktop",
    depth: int = 10,
    stop_on_domain: str | None = None,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """The live results page for one keyword: organic results, features and AI-overview
    citations."""
    async with unit_of_work() as db:
        return await seo_data.serp_snapshot(
            db, caller(), keyword, device, depth, stop_on_domain, location_code, language_code
        )


@tool(provider=DOMAIN)
async def seo_trend(
    keywords: list[str], location_code: int | None = None, language_code: str | None = None
) -> dict:
    """Daily interest over time for keywords. Five keywords per vendor call."""
    async with unit_of_work() as db:
        return await seo_data.trend(db, caller(), keywords, location_code, language_code)


@tool(provider=DOMAIN)
async def seo_domain_overview(
    domain: str, location_code: int | None = None, language_code: str | None = None
) -> dict:
    """Organic traffic estimate and ranking-keyword count for a domain."""
    async with unit_of_work() as db:
        return await seo_data.domain_overview(db, caller(), domain, location_code, language_code)


@tool(provider=DOMAIN)
async def seo_serp_competitors(
    keywords: list[str],
    limit: int = 10,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """Domains that appear most on the results pages of the given keywords (up to 100),
    ranked by visibility."""
    async with unit_of_work() as db:
        return await seo_data.serp_competitors(
            db, caller(), keywords, limit, location_code, language_code
        )


@tool(provider=DOMAIN)
async def seo_relevant_pages(
    domain: str,
    limit: int = 100,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """A domain's pages ordered by organic traffic, with the keyword count each ranks for."""
    async with unit_of_work() as db:
        return await seo_data.relevant_pages(
            db, caller(), domain, limit, location_code, language_code
        )


@tool(provider=DOMAIN)
async def seo_lighthouse(url: str, strategy: Literal["mobile", "desktop"] = "mobile") -> dict:
    """Run Lighthouse on one URL for mobile or desktop and return the raw report."""
    async with unit_of_work() as db:
        return await seo_data.lighthouse(db, caller(), url, strategy)


@tool(provider=DOMAIN)
async def seo_llm_mentions(
    targets: list[LlmTarget],
    platform: Literal["chat_gpt", "google"] = "google",
    limit: int = 300,
    location_code: int | None = None,
    language_code: str | None = None,
) -> dict:
    """Prompts on an AI platform whose answers mention a domain or keyword, with cited URLs
    and co-mentioned brands."""
    async with unit_of_work() as db:
        return await seo_data.llm_mentions(
            db,
            caller(),
            [t.model_dump() for t in targets],
            platform,
            limit,
            location_code,
            language_code,
        )
