from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_structure import repository as repo
from src.site_structure.constants import SCREEN_CONFIDENCE
from src.site_structure.schemas import LinkSuggestionChanges, ScreeningInput, ScreenResult

log = get_logger("site_structure.screening")

DEFAULT_ASK = {
    "create": "Should the source passage gain a link to the target page?",
    "delete": "Should the existing link from the source page to the target page be removed?",
    "edit": "Should the existing link from the source page to the target page be changed as the suggestion proposes?",
}


def questions(action: str, question: str | None) -> dict[str, Question]:
    ask = question or DEFAULT_ASK[action]
    return {
        "apply": choice(
            f"{ask} Judge from the source text, the target page and the suggestion. "
            "Say yes only when a reader of the source would plausibly want the target next "
            "and the change fits how the page is written.",
            {
                "yes": "the change is worth making: the target is relevant to the source passage and the suggestion holds",
                "no": "the change is not worth making: the pages are unrelated, the suggestion is weak, or the link would read as spam",
            },
        )
    }


def screening_state(item: ScreeningInput) -> dict[str, Any]:
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


def yes_confidence(answer: dict[str, Any]) -> float:
    probabilities = answer.get("probabilities")
    if isinstance(probabilities, dict) and isinstance(probabilities.get("yes"), (int, float)):
        return float(probabilities["yes"])
    confidence = answer.get("confidence")
    sure = float(confidence) if isinstance(confidence, (int, float)) else 0.5
    return sure if answer.get("choice") == "yes" else 1.0 - sure


def rejected(confidence_yes: float) -> bool:
    return 1.0 - confidence_yes >= SCREEN_CONFIDENCE


async def screen_one(
    db: AsyncSession, caller: Caller, item: ScreeningInput, question: str | None
) -> float | None:
    subject = {
        "suggestion_id": item.id,
        "from_hash": item.from_content_hash,
        "to_hash": item.to_content_hash,
        "question": question,
    }
    try:
        result = await json_data_extractor.decide(
            db, caller, subject, screening_state(item), questions(item.action, question)
        )
    except ProviderRequestError as exc:
        log.warning("link suggestion screening failed", suggestion_id=item.id, error=str(exc))
        return None
    confidence = yes_confidence(result["answers"]["apply"])
    await repo.update_one(
        db,
        caller.site_id or "",
        item.id,
        LinkSuggestionChanges(
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
    question: str | None,
) -> ScreenResult:
    caller = Caller(user_id=user_id, site_id=site_id)
    items = await repo.screening_inputs(db, site_id, job_id, ids, limit)
    result = ScreenResult()
    for item in items:
        try:
            confidence = await screen_one(db, caller, item, question)
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
