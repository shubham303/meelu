import pycountry
from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.seo_data.shape import locale_of
from src.sites.service import site_service

DEFAULT_LANGUAGE = "en"

ENGLISH_MARKETS = ("US", "GB", "CA", "AU", "IE", "NZ")

COUNTRY_LOCATION_BASE = 2000


def location_code(country: str) -> int:
    return COUNTRY_LOCATION_BASE + int(pycountry.countries.get(alpha_2=country).numeric)


def country_of(location: int) -> str | None:
    found = pycountry.countries.get(numeric=str(location - COUNTRY_LOCATION_BASE).zfill(3))
    return found.alpha_2 if found else None


def markets(
    site_markets: list[str], site_language: str | None, location: int | None = None
) -> list[dict]:
    language = site_language or DEFAULT_LANGUAGE
    if location:
        return [locale_of(location, language)]
    countries = site_markets or (ENGLISH_MARKETS if language == DEFAULT_LANGUAGE else [])
    if not countries:
        raise ValueError(
            "This website's market is not set. Ask the user which countries it sells to "
            "and save them on the website record."
        )
    return [locale_of(location_code(c), language) for c in countries]


async def site_markets(
    db: AsyncSession, user_id: str, site_id: str, location: int | None = None
) -> list[dict]:
    site = await site_service.get(db, user_id, site_id)
    return markets(site.markets, site.language, location)
