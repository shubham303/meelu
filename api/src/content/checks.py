import re
from dataclasses import dataclass

from src.content.schemas.pieces import PieceCheck

TITLE_MAX = 60
META_MIN = 70
META_MAX = 160
BODY_H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
IMAGE_LINE_RE = re.compile(r"^\s*!\[")

WARN = "warn"


@dataclass(frozen=True)
class PageFields:
    title: str
    h1: str
    meta_description: str
    target_keyword: str | None
    body_markdown: str


def _check(code: str, message: str) -> PieceCheck:
    return PieceCheck(code=code, level=WARN, message=message)


def first_paragraph(markdown: str) -> str:
    for block in re.split(r"\n\s*\n", markdown):
        text = block.strip()
        if text and not HEADING_RE.match(text) and not IMAGE_LINE_RE.match(text):
            return text
    return ""


def _contains(haystack: str, keyword: str) -> bool:
    return keyword in " ".join(haystack.lower().split())


def run_checks(page: PageFields) -> list[PieceCheck]:
    checks: list[PieceCheck] = []

    if len(page.title) > TITLE_MAX:
        checks.append(
            _check(
                "title_length",
                f"Search results cut titles past about {TITLE_MAX} characters; "
                f"this is {len(page.title)}.",
            )
        )

    if not page.h1:
        checks.append(_check("h1_missing", "The page has no H1."))

    meta = page.meta_description
    if not meta:
        checks.append(_check("meta_description_missing", "The page has no meta description."))
    elif not META_MIN <= len(meta) <= META_MAX:
        checks.append(
            _check(
                "meta_description_length",
                f"A meta description reads best at {META_MIN}–{META_MAX} characters; "
                f"this is {len(meta)}.",
            )
        )

    if BODY_H1_RE.search(page.body_markdown):
        checks.append(
            _check(
                "body_h1",
                "The body has its own H1. The page's H1 is its own field; start the body's "
                "headings at H2.",
            )
        )

    keyword = page.target_keyword
    if keyword:
        places = {
            "title": page.title,
            "H1": page.h1,
            "meta description": meta,
            "first paragraph": first_paragraph(page.body_markdown),
        }
        missing = [name for name, text in places.items() if not _contains(text, keyword)]
        if missing:
            checks.append(
                _check(
                    "keyword_placement",
                    f'The target keyword "{keyword}" is missing from the {", ".join(missing)}.',
                )
            )

    return checks
