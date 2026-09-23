from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.llm_judge.service import llm_judge
from src.providers.registry import Caller
from src.site_structure.pillars import repository as repo
from src.site_structure.review import VERDICTS
from src.site_structure.schemas import PillarPageSuggestionChanges, PillarReviewInput, ReviewResult

log = get_logger("site_structure.pillars.review")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "title": {"type": "string"},
        "suggestion": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict", "title", "suggestion", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed pillar page for a website: a hub that introduces a topic and links to every page the site already has on it. Decide whether the owner should build it.

The owner's brief for this run:
{prompt}

Answer with a verdict: "ready" when the pages form one topic a reader would expect a single page to cover and the site has no such page, "llm_rejected" when they are a loose mix, the topic is too broad or too thin, or an existing page already does the job. When the action is "expand", judge whether the named existing page should grow into that hub.

When the verdict is ready, write the title the pillar page should carry and a suggestion the owner can act on: what the page must cover, which of the listed pages it should link to and in what order, and which of them should link back. Otherwise leave title and suggestion empty. Give a one-sentence reason."""


def review_state(item: PillarReviewInput) -> dict[str, Any]:
    return {
        "action": item.action,
        "topic": item.topic,
        "cohesion": item.search_score,
        "covering_page": {"url": item.covering_url or "", "title": item.covering_title or ""},
        "pages": item.members,
    }


async def review_one(
    db: AsyncSession, caller: Caller, item: PillarReviewInput, prompt: str
) -> str | None:
    subject = {
        "pillar_id": item.id,
        "members": sorted(m["url"] for m in item.members),
        "prompt": prompt,
    }
    try:
        result = await llm_judge.judge(
            db, caller, subject, INSTRUCTIONS.format(prompt=prompt), review_state(item), SCHEMA
        )
    except ProviderRequestError as exc:
        log.warning("pillar suggestion review failed", suggestion_id=item.id, error=str(exc))
        return None
    answer = result["answer"]
    verdict = answer.get("verdict")
    if verdict not in VERDICTS:
        log.warning("pillar suggestion review gave no verdict", suggestion_id=item.id)
        return None
    changes = PillarPageSuggestionChanges(state=verdict)
    if verdict == "ready":
        if answer.get("title"):
            changes.topic = str(answer["title"]).strip()
        if answer.get("suggestion"):
            changes.suggestion = str(answer["suggestion"]).strip()
    await repo.update_one(db, caller.site_id or "", item.id, changes)
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
    items = await repo.review_inputs(db, site_id, job_id, ids, limit, unscreened_only=False)
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
