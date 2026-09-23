from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_structure.pillars import repository as repo
from src.site_structure.schemas import PillarPageSuggestionChanges, PillarReviewInput, ScreenResult
from src.site_structure.screening import rejected, yes_confidence

log = get_logger("site_structure.pillars.screening")

ASK = {
    "create": "Do these pages form one coherent topic that deserves a single hub page introducing and linking all of them?",
    "expand": "Should the existing page be expanded into the hub that introduces and links all of these pages?",
}


def questions(action: str) -> dict[str, Question]:
    return {
        "apply": choice(
            f"{ASK[action]} Judge from the page titles, descriptions and URLs. Say yes only "
            "when a reader would expect one page to cover the whole set.",
            {
                "yes": "the pages share one clear topic and a hub page for them would help a reader",
                "no": "the pages are a loose mix, the topic is too broad or too thin, or a hub already covers them",
            },
        )
    }


def screening_state(item: PillarReviewInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "topic": item.topic,
        "covering_page": {"url": item.covering_url or "", "title": item.covering_title or ""},
        "pages": [
            {"url": m["url"], "title": m["title"], "meta_description": m["meta_description"]}
            for m in item.members
        ],
    }


async def screen_one(db: AsyncSession, caller: Caller, item: PillarReviewInput) -> float | None:
    subject = {"pillar_id": item.id, "members": sorted(m["url"] for m in item.members)}
    try:
        result = await json_data_extractor.decide(
            db, caller, subject, screening_state(item), questions(item.action)
        )
    except ProviderRequestError as exc:
        log.warning("pillar suggestion screening failed", suggestion_id=item.id, error=str(exc))
        return None
    confidence = yes_confidence(result["answers"]["apply"])
    await repo.update_one(
        db,
        caller.site_id or "",
        item.id,
        PillarPageSuggestionChanges(
            state="llm_rejected" if rejected(confidence) else "draft", confidence=confidence
        ),
    )
    return confidence


async def screen(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str | None,
    ids: list[str] | None,
    limit: int,
) -> ScreenResult:
    caller = Caller(user_id=user_id, site_id=site_id)
    items = await repo.review_inputs(db, site_id, job_id, ids, limit, unscreened_only=True)
    result = ScreenResult()
    for item in items:
        try:
            confidence = await screen_one(db, caller, item)
        except (NoProviderError, InsufficientCreditsError) as exc:
            result.stopped = str(exc)
            break
        if confidence is None:
            result.failed += 1
            continue
        result.screened += 1
        if rejected(confidence):
            result.llm_rejected += 1
        else:
            result.passed += 1
    return result
