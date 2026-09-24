from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.llm_judge.service import llm_judge
from src.providers.registry import Caller
from src.site_structure import repository as repo
from src.site_structure.schemas import LinkSuggestionChanges, ReviewResult, ScreeningInput

log = get_logger("site_structure.review")

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


async def review_one(
    db: AsyncSession, caller: Caller, item: ScreeningInput, prompt: str
) -> str | None:
    subject = {
        "suggestion_id": item.id,
        "from_hash": item.from_content_hash,
        "to_hash": item.to_content_hash,
        "prompt": prompt,
    }
    try:
        result = await llm_judge.judge(
            db,
            caller,
            subject,
            INSTRUCTIONS.format(prompt=prompt),
            review_state(item),
            SCHEMA,
        )
    except ProviderRequestError as exc:
        log.warning("link suggestion review failed", suggestion_id=item.id, error=str(exc))
        return None
    verdict = result["answer"].get("verdict")
    if verdict not in VERDICTS:
        log.warning("link suggestion review gave no verdict", suggestion_id=item.id)
        return None
    await repo.update_one(db, caller.site_id or "", item.id, LinkSuggestionChanges(state=verdict))
    return verdict


async def review(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    prompt: str,
    job_id: str | None,
    ids: list[str] | None,
    limit: int,
) -> ReviewResult:
    caller = Caller(user_id=user_id, site_id=site_id)
    items = await repo.review_inputs(db, site_id, job_id, ids, limit)
    result = ReviewResult()
    for item in items:
        try:
            verdict = await review_one(db, caller, item, prompt)
        except (NoProviderError, InsufficientCreditsError) as exc:
            result.stopped = str(exc)
            break
        if verdict is None:
            result.failed += 1
            continue
        result.reviewed += 1
        setattr(result, verdict, getattr(result, verdict) + 1)
    return result
