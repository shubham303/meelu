from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.page_suggestions.repository import seo_page_suggestions
from src.seo.pipeline.review_inputs import has_serp_evidence, seo_review_input_service
from src.seo.pipeline.schemas import ReviewBatch, ReviewItem, ReviewResult, Verdict

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


class SeoReviewService:
    async def review_inputs(
        self,
        db: AsyncSession,
        site_id: str,
        job_id: str,
        prompt: str,
        ids: list[str] | None,
        limit: int,
    ) -> ReviewBatch:
        rows = await seo_page_suggestions.list_for_job(db, site_id, job_id, ids, ("draft",), limit)
        items: list[ReviewItem] = []
        needs_serp: list[str] = []
        seen: set[str] = set()
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            if row.pair_id:
                seen.add(row.pair_id)
            state = await seo_review_input_service.review_state(db, site_id, row)
            if row.action == "add" and not has_serp_evidence(state):
                needs_serp.append(row.id)
                continue
            items.append(ReviewItem(id=row.id, state=state))
        return ReviewBatch(
            instructions=INSTRUCTIONS.format(prompt=prompt),
            schema=SCHEMA,
            items=items,
            needs_serp=needs_serp,
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, verdicts: list[Verdict]
    ) -> ReviewResult:
        result = ReviewResult()
        for given in verdicts:
            if given.verdict not in VERDICTS:
                result.failed += 1
                continue
            row = await seo_page_suggestions.get(db, site_id, given.id)
            if row is None:
                result.failed += 1
                continue
            patch = {"state": given.verdict}
            written = (given.suggestion or "").strip()
            if given.verdict == "reviewed" and written:
                patch["suggestion"] = written[:4000]
            await seo_page_suggestions.update(db, site_id, row.id, patch)
            if row.pair_id:
                await seo_page_suggestions.update(
                    db, site_id, row.pair_id, {"state": given.verdict}
                )
            await db.commit()
            if given.verdict == "reviewed":
                result.reviewed += 1
            else:
                result.llm_rejected += 1
        return result


seo_review_service = SeoReviewService()
