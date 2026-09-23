import re
from typing import Any
from urllib.parse import urlparse

MAX_RAW_TEXT = 4000
EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$")


def string_or_none(value: Any) -> str | None:
    s = str(value or "").strip()
    return s or None


def url_or_none(value: Any) -> str | None:
    s = str(value or "").strip()
    if not s:
        return None
    candidate = s if "://" in s else f"https://{s}"
    parsed = urlparse(candidate)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return candidate


def email_or_none(value: Any) -> str | None:
    s = str(value or "").strip().lower()
    return s if EMAIL.fullmatch(s) else None


def handle_from_url(url: Any) -> str | None:
    try:
        parts = [p for p in urlparse(str(url)).path.split("/") if p]
    except ValueError:
        return None
    return parts[-1] if parts else None


def prospect(source: str, raw: dict[str, Any]) -> dict | None:
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    website = url_or_none(raw.get("website"))
    source_url = url_or_none(raw.get("sourceUrl"))
    handles = {}
    for platform, handle in (raw.get("channelHandles") or {}).items():
        clean = str(handle or "").strip().lstrip("@")
        if clean:
            handles[platform] = clean
    if not website and not source_url and not handles:
        return None
    return {
        "name": name,
        "company": string_or_none(raw.get("company")),
        "role": string_or_none(raw.get("role")),
        "email": email_or_none(raw.get("email")),
        "website": website,
        "channelHandles": handles,
        "source": source,
        "sourceUrl": source_url,
        "rawText": str(raw.get("rawText") or "").strip()[:MAX_RAW_TEXT],
    }
