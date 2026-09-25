from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.site_structure import repository as repo
from src.site_structure.schemas import (
    LinkSuggestionChanges,
    ReviewBatch,
    ReviewItem,
    ReviewResult,
    ScreeningInput,
    Verdict,
)

VERDICTS = ("ready", "llm_rejected")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed internal link on a website and decide whether it should be shown to the site owner.

The owner's brief for this run:
{prompt}

Answer with a verdict: "ready" when the link is worth the owner's time as the brief describes, "llm_rejected" when it is not. Judge from the source passage, the target page and the suggestion text. A link is not worth it when the pages are unrelated, when the passage does not really discuss what the target is about, when the passage is boilerplate, or when the link would read as spam to a reader. Give a one-sentence reason."""


def review_state(item: ScreeningInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "suggestion": item.suggestion,
        "source": {
            "url": item.from_url,
            "title": item.from_title or "",
            "text": item.from_text,
            "anchor": item.anchor or "",
        },
        "target": {
            "url": item.to_url,
            "title": item.to_title or "",
            "meta_description": item.to_meta_description or "",
            "h1": item.to_h1,
            "page_type": item.to_page_type or "",
        },
    }


async def review_inputs(
    db: AsyncSession,
    site_id: str,
    prompt: str,
    job_id: str | None,
    ids: list[str] | None,
    limit: int,
) -> ReviewBatch:
    items = await repo.review_inputs(db, site_id, job_id, ids, limit)
    return ReviewBatch(
        instructions=INSTRUCTIONS.format(prompt=prompt),
        schema=SCHEMA,
        items=[ReviewItem(id=item.id, state=review_state(item)) for item in items],
    )


async def apply_verdicts(db: AsyncSession, site_id: str, verdicts: list[Verdict]) -> ReviewResult:
    result = ReviewResult()
    for given in verdicts:
        if given.verdict not in VERDICTS:
            result.failed += 1
            continue
        updated = await repo.update_one(
            db, site_id, given.id, LinkSuggestionChanges(state=given.verdict)
        )
        if updated is None:
            result.failed += 1
            continue
        result.reviewed += 1
        setattr(result, given.verdict, getattr(result, given.verdict) + 1)
    return result
