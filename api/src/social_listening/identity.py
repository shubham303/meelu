import hashlib
import re
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

HOST_PREFIXES = ("www.", "m.", "mobile.", "old.", "new.", "np.")
HOST_ALIASES = {"twitter.com": "x.com", "redd.it": "reddit.com", "youtu.be": "youtube.com"}
KEPT_QUERY_PARAMS = ("id", "v")
REDDIT_FULLNAME = re.compile(r"^t[1-6]_")
REDDIT_COMMENTS_PATH = re.compile(r"^(/r/[^/]+/comments/[^/]+)(/.*)?$", re.IGNORECASE)
URL_PATTERN = re.compile(r"https?://\S+")
NON_WORD = re.compile(r"[^\w]+")
MIN_HASHED_CHARS = 80

PATH_IDS = {
    "reddit": (re.compile(r"/comments/([a-z0-9]+)", re.IGNORECASE), lambda m, _: m.group(1).lower()),
    "x": (re.compile(r"/status(?:es)?/(\d+)"), lambda m, _: m.group(1)),
    "stackexchange": (re.compile(r"/(?:questions|q)/(\d+)"), lambda m, host: f"{host}-{m.group(1)}"),
    "github": (
        re.compile(r"^/([^/]+)/([^/]+)/(?:issues|pull|discussions)/(\d+)"),
        lambda m, _: f"{m.group(1).lower()}/{m.group(2).lower()}#{m.group(3)}",
    ),
    "bluesky": (
        re.compile(r"/profile/([^/]+)/post/([^/]+)"),
        lambda m, _: f"{m.group(1).lower()}/{m.group(2)}",
    ),
    "linkedin": (re.compile(r"activity[-:](\d+)"), lambda m, _: m.group(1)),
    "instagram": (re.compile(r"/(?:p|reel|tv)/([^/]+)"), lambda m, _: m.group(1)),
    "tiktok": (re.compile(r"/video/(\d+)"), lambda m, _: m.group(1)),
    "youtube": (re.compile(r"/(?:shorts|embed|live)/([^/?]+)"), lambda m, _: m.group(1)),
}


def _host(parts) -> str:
    host = (parts.hostname or "").lower()
    for prefix in HOST_PREFIXES:
        if host.startswith(prefix):
            host = host[len(prefix) :]
            break
    return HOST_ALIASES.get(host, host)


def _split(url: str):
    raw = url.strip()
    return urlsplit(raw if "://" in raw else f"https://{raw}")


def canonical_url(url: str) -> str:
    parts = _split(url)
    host = _host(parts)
    path = re.sub(r"/{2,}", "/", parts.path or "")
    if host == "reddit.com":
        match = REDDIT_COMMENTS_PATH.match(path)
        if match:
            path = match.group(1)
        path = path.lower()
    path = path.rstrip("/")
    query = urlencode(
        sorted((k, v) for k, v in parse_qsl(parts.query) if k in KEPT_QUERY_PARAMS)
    )
    return urlunsplit(("https", host, path, query, ""))


def id_from_url(platform: str, url: str) -> str | None:
    parts = _split(url)
    if platform == "hackernews":
        values = parse_qs(parts.query).get("id")
        return values[0] if values else None
    if platform == "youtube":
        values = parse_qs(parts.query).get("v")
        if values:
            return values[0]
        if _host(parts) == "youtube.com" and (parts.hostname or "").endswith("youtu.be"):
            return parts.path.strip("/") or None
    rule = PATH_IDS.get(platform)
    if rule is None:
        return None
    pattern, build = rule
    match = pattern.search(parts.path or "")
    return build(match, _host(parts)) if match else None


def native_id(platform: str, external_id: str | None, url: str) -> str | None:
    from_url = id_from_url(platform, url)
    if from_url:
        return from_url
    value = (external_id or "").strip()
    if not value or value == url.strip() or value.startswith("http"):
        return None
    if platform == "reddit":
        return REDDIT_FULLNAME.sub("", value).lower()
    return value


def post_key(platform: str, external_id: str | None, url: str) -> str:
    own = native_id(platform, external_id, url)
    if own is not None:
        return f"{platform}:{own}"
    return f"url:{canonical_url(url)}"


def content_hash(title: str | None, text: str | None) -> str | None:
    body = URL_PATTERN.sub(" ", f"{title or ''} {text or ''}".lower())
    normalized = " ".join(NON_WORD.sub(" ", body).split())
    if len(normalized) < MIN_HASHED_CHARS:
        return None
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]
