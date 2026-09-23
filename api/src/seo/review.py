from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.llm_judge.service import llm_judge
from src.providers.registry import Caller
from src.seo import repository as repo
from src.seo.review_inputs import has_serp_evidence, review_state
from src.seo.schemas import PageSuggestionRecord, ReviewResult
from src.seo.screening import content_hash

log = get_logger("seo.review")

VERDICTS = ("reviewed", "llm_rejected")

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "reason": {"type": "string"},
        "suggestion": {"type": "string"},
    },
    "required": ["verdict", "reason", "suggestion"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You review one proposed change to a website's pages — add a page, edit a page, or delete and merge a page — and decide whether it should be shown to the site owner.

The owner's brief for this run:
{prompt}

Answer with a verdict: "reviewed" when the change is worth the owner's time as the brief describes, "llm_rejected" when it is not. Judge from the evidence, the page, the keywords and the search results when given. Reject when the topic is off the site's business, when the evidence is thin, when an edit would not plausibly move the keywords listed, or when a delete would lose something the site needs. When the item is a pair (an edit plus the delete it absorbs), judge them as one change.

Then write the suggestion the owner acts on. For an add: a working title and what the page must cover, in a few sentences. For an edit: the concrete changes, one per sentence. For a delete: where the page redirects and why. Give a one-sentence reason."""


async def review_one(
    db: AsyncSession, caller: Caller, row: PageSuggestionRecord, prompt: str
) -> str | None:
    site_id = caller.site_id or ""
    state = await review_state(db, site_id, row)
    if row.action == "add" and not has_serp_evidence(state):
        return "needs_serp"
    subject = {"suggestion_id": row.id, "content": content_hash(row), "prompt": prompt}
    try:
        result = await llm_judge.judge(
            db, caller, subject, INSTRUCTIONS.format(prompt=prompt), state, SCHEMA
        )
    except ProviderRequestError as exc:
        log.warning("page suggestion review failed", suggestion_id=row.id, error=str(exc))
        return None
    answer = result["answer"]
    verdict = answer.get("verdict")
    if verdict not in VERDICTS:
        log.warning("page suggestion review gave no verdict", suggestion_id=row.id)
        return None
    patch = {"state": verdict}
    written = str(answer.get("suggestion") or "").strip()
    if verdict == "reviewed" and written:
        patch["suggestion"] = written[:4000]
    await repo.update_suggestion(db, site_id, row.id, patch)
    if row.pair_id:
        await repo.update_suggestion(db, site_id, row.pair_id, {"state": verdict})
    return verdict


async def review(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    prompt: str,
    ids: list[str] | None,
    limit: int,
) -> ReviewResult:
    caller = Caller(user_id=user_id, site_id=site_id)
    rows = await repo.job_rows(db, site_id, job_id, ids, ("draft",), limit)
    result = ReviewResult()
    seen: set[str] = set()
    for row in rows:
        if row.id in seen:
            continue
        seen.add(row.id)
        if row.pair_id:
            seen.add(row.pair_id)
        try:
            verdict = await review_one(db, caller, row, prompt)
        except (NoProviderError, InsufficientCreditsError) as exc:
            result.stopped = str(exc)
            break
        await db.commit()
        if verdict is None:
            result.failed += 1
        elif verdict == "needs_serp":
            result.needs_serp.append(row.id)
        elif verdict == "reviewed":
            result.reviewed += 1
        else:
            result.llm_rejected += 1
    return result
