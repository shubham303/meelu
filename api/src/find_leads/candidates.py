import re
from typing import Any

from src.find_leads.identity import author_key, profile_url, usable_handle, web_key
from src.find_leads.schemas import MAX_EVIDENCE, WEB_PLATFORM, CandidateItem
from src.providers.social_search.platforms import WEB_SEARCHED_PLATFORMS

LINKEDIN_PROFILE = re.compile(r"linkedin\.com/in/([^/?#]+)", re.IGNORECASE)


def candidate_stats_key(source: str, platform: str) -> str | None:
    if source == WEB_PLATFORM and platform == WEB_PLATFORM:
        return WEB_PLATFORM
    if source == "linkedin" and platform == "linkedin":
        return "linkedin"
    if source == "posts" and platform in WEB_SEARCHED_PLATFORMS:
        return f"posts:{platform}"
    return None


def linkedin_slug(url: str | None) -> str | None:
    match = LINKEDIN_PROFILE.search(url or "")
    return match.group(1).lower() if match else None


def candidate_row(source: str, platform: str, item: CandidateItem) -> dict[str, Any] | None:
    base = {
        "source": source,
        "platform": platform,
        "name": item.name,
        "headline": item.headline,
        "snippet": item.snippet,
        "evidence": [e.model_dump() for e in item.evidence][:MAX_EVIDENCE],
    }
    if source == "linkedin":
        slug = linkedin_slug(item.profile_url)
        if slug is None:
            return None
        return {
            **base,
            "identity_key": f"linkedin:{slug}",
            "handle": None,
            "profile_url": f"https://www.linkedin.com/in/{slug}/",
        }
    if source == "posts":
        handle = usable_handle(item.handle)
        if handle is None:
            return None
        return {
            **base,
            "identity_key": author_key(platform, handle),
            "handle": handle,
            "name": item.name or handle,
            "profile_url": item.profile_url or profile_url(platform, handle),
        }
    email = (item.email or "").strip().lower() or None
    if email and not item.email_source_url:
        email = None
    key = web_key(email, item.website, item.profile_url)
    if key is None:
        return None
    return {
        **base,
        "identity_key": key,
        "website": item.website,
        "profile_url": item.profile_url,
        "email": email,
        "email_source_url": item.email_source_url if email else None,
    }
