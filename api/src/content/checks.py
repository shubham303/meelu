import re

from src.content.platform_seeds import PlatformSeed
from src.content.schemas.pieces import PieceCheck

LINK_RE = re.compile(r"https?://[^\s)\]>]+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"(?<![\w&])#[A-Za-z][\w]*")

BLOCK = "block"
WARN = "warn"


def _check(code: str, level: str, message: str) -> PieceCheck:
    return PieceCheck(code=code, level=level, message=message)


def count_links(text: str) -> int:
    return len(LINK_RE.findall(text))


def count_hashtags(text: str) -> int:
    return len(HASHTAG_RE.findall(text))


def run_checks(
    seed: PlatformSeed, body: str, *, media_count: int, site_host: str | None
) -> list[PieceCheck]:
    checks: list[PieceCheck] = []
    length = len(body)

    if seed.character_limit and length > seed.character_limit:
        checks.append(
            _check(
                "character_limit",
                BLOCK,
                f"{seed.label} allows {seed.character_limit} characters; this is {length}. "
                f"Cut {length - seed.character_limit}.",
            )
        )

    links = count_links(body)
    if seed.max_links is not None and links > seed.max_links:
        noun = "links" if seed.max_links != 1 else "link"
        allowed = "no links" if seed.max_links == 0 else f"at most {seed.max_links} {noun}"
        checks.append(
            _check(
                "max_links", BLOCK, f"{seed.label} takes {allowed} in the body; this has {links}."
            )
        )

    hashtags = count_hashtags(body)
    if seed.max_hashtags is not None and hashtags > seed.max_hashtags:
        allowed = (
            "no hashtags" if seed.max_hashtags == 0 else f"at most {seed.max_hashtags} hashtags"
        )
        checks.append(
            _check(
                "max_hashtags",
                WARN,
                f"{seed.label} works best with {allowed}; this has {hashtags}.",
            )
        )

    if seed.requires_media and media_count == 0:
        checks.append(
            _check("requires_media", BLOCK, f"{seed.label} won't take a post without an image.")
        )
    if seed.max_media and media_count > seed.max_media:
        checks.append(
            _check(
                "max_media",
                BLOCK,
                f"{seed.label} allows {seed.max_media} media items; this has {media_count}.",
            )
        )

    if not seed.allows_promotion and site_host:
        if site_host.lower() in body.lower():
            checks.append(
                _check(
                    "no_promotion",
                    BLOCK,
                    f"{seed.label} treats links to your own site as self-promotion. Remove them.",
                )
            )

    return checks


def is_blocked(checks: list[PieceCheck]) -> bool:
    return any(c.level == BLOCK for c in checks)
