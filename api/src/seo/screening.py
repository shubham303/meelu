import hashlib
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.seo.constants import SCREEN_CONFIDENCE
from src.seo.repositories import seo_page_suggestions
from src.seo.review_inputs import seo_review_input_service
from src.seo.schemas import PageSuggestionRecord, ScreenResult

log = get_logger("seo.screening")

DEFAULT_ASK = {
    "add": "Would a new page on this topic be worth writing for this site, given what it already has?",
    "edit": "Would this change plausibly improve the page for the keywords listed?",
    "delete": "Is this page safe to remove or merge into the target without losing something the site needs?",
}


def questions(action: str, question: str | None) -> dict[str, Question]:
    ask = question or DEFAULT_ASK[action]
    return {
        "apply": choice(
            f"{ask} Judge from the evidence, the page and the keywords.",
            {
                "yes": "worth the owner's time: the evidence supports the change",
                "no": "not worth it: the topic is off the site's business, the evidence is thin, or the change would not help",
            },
        )
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


def content_hash(row: PageSuggestionRecord) -> str:
    payload = json.dumps([row.suggestion, row.evidence], sort_keys=True, default=str)
    return hashlib.sha1(payload.encode()).hexdigest()[:16]


class SeoScreeningService:
    async def screen_one(
        self, db: AsyncSession, caller: Caller, row: PageSuggestionRecord, question: str | None
    ) -> float | None:
        subject = {"suggestion_id": row.id, "content": content_hash(row), "question": question}
        state = await seo_review_input_service.review_state(db, caller.site_id or "", row)
        try:
            result = await json_data_extractor.decide(
                db, caller, subject, state, questions(row.action, question)
            )
        except ProviderRequestError as exc:
            log.warning("page suggestion screening failed", suggestion_id=row.id, error=str(exc))
            return None
        confidence = yes_confidence(result["answers"]["apply"])
        await seo_page_suggestions.update(
            db,
            caller.site_id or "",
            row.id,
            {
                "state": "llm_rejected" if rejected(confidence) else "draft",
                "confidence": confidence,
            },
        )
        return confidence

    async def screen(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        ids: list[str] | None,
        question: str | None,
        limit: int,
    ) -> ScreenResult:
        caller = Caller(user_id=user_id, site_id=site_id)
        rows = await seo_page_suggestions.list_for_job(db, site_id, job_id, ids, ("draft",), limit)
        result = ScreenResult()
        for row in rows:
            try:
                confidence = await self.screen_one(db, caller, row, question)
            except (NoProviderError, InsufficientCreditsError) as exc:
                result.stopped = str(exc)
                break
            await db.commit()
            if confidence is None:
                result.failed += 1
                continue
            result.screened += 1
            if rejected(confidence):
                result.llm_rejected += 1
            else:
                result.passed += 1
        return result


seo_screening_service = SeoScreeningService()
