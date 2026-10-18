import re
from urllib.parse import quote, urlsplit

IGNORED_HANDLES = frozenset({"", "unknown", "[deleted]", "deleted", "automoderator", "anonymous"})
PUBLIC_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,99}$")

PROFILE_URLS = {
    "reddit": "https://www.reddit.com/user/{}/",
    "x": "https://x.com/{}",
    "bluesky": "https://bsky.app/profile/{}",
    "hackernews": "https://news.ycombinator.com/user?id={}",
    "github": "https://github.com/{}",
    "devto": "https://dev.to/{}",
}


def usable_handle(handle: str | None) -> str | None:
    clean = (handle or "").strip().lstrip("@")
    if clean.lower().startswith("u/"):
        clean = clean[2:]
    return None if clean.lower() in IGNORED_HANDLES else clean


def author_key(platform: str, handle: str) -> str:
    return f"{platform}:{handle.lower()}"


def profile_url(platform: str, handle: str) -> str | None:
    if platform == "linkedin":
        return f"https://www.linkedin.com/in/{handle}/" if PUBLIC_IDENTIFIER.match(handle) else None
    template = PROFILE_URLS.get(platform)
    return template.format(quote(handle, safe="._-")) if template else None


def domain_of(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    host = (urlsplit(raw if "://" in raw else f"https://{raw}").hostname or "").lower()
    return host[4:] if host.startswith("www.") else host or None


def web_key(email: str | None, website: str | None, page_url: str | None) -> str | None:
    if email and "@" in email:
        return f"email:{email.strip().lower()}"
    domain = domain_of(website) or domain_of(page_url)
    return f"web:{domain}" if domain else None
