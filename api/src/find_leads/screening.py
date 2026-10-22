import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.find_leads.jobs import JobResult
from src.find_leads.models.lead import Lead
from src.find_leads.repositories.briefs import lead_briefs
from src.find_leads.repositories.leads import leads
from src.find_leads.repositories.runs import lead_runs
from src.find_leads.repositories.seen import lead_seen
from src.find_leads.schemas import MAX_CANDIDATES_PER_RUN, SEEN_JUDGED
from src.providers.json_data_extractor.adapter import Question, choice
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller

SCREEN_BATCH = 100
SCREEN_CONCURRENCY = 3
SNIPPET_CHARS = 500
QUOTE_CHARS = 240

FITS = {
    "yes": "the person fits what the brief asks for",
    "no": "the person does not fit what the brief asks for",
}

INSTRUCTIONS = (
    "Does this person fit the brief? Judge only by what the brief asks for and add no rule "
    "of your own. Person: "
)


def person_text(lead: Lead) -> str:
    quotes = " | ".join(
        str(e.get("quote") or "")[:QUOTE_CHARS] for e in lead.evidence or [] if e.get("quote")
    )
    parts = [
        f"{lead.platform}: {lead.name or ''}" + (f" (@{lead.handle})" if lead.handle else ""),
        f"Headline: {lead.headline}" if lead.headline else "",
        f"Found by: {str(lead.snippet)[:SNIPPET_CHARS]}" if lead.snippet else "",
        f"They wrote: {quotes}" if quotes else "",
    ]
    return ". ".join(p for p in parts if p)


def questions(batch: list[Lead]) -> dict[str, Question]:
    return {
        f"p{seat}": choice(INSTRUCTIONS + person_text(lead), FITS)
        for seat, lead in enumerate(batch)
    }


def batches(rows: list[Lead], briefs: dict[str, str]) -> list[tuple[str, list[Lead]]]:
    fallback = " / ".join(briefs.values())
    groups: dict[str, list[Lead]] = {}
    for row in rows:
        groups.setdefault(row.brief_id if row.brief_id in briefs else "", []).append(row)
    return [
        (briefs.get(key, fallback), own[start : start + SCREEN_BATCH])
        for key, own in groups.items()
        for start in range(0, len(own), SCREEN_BATCH)
    ]


async def drop_leads(db: AsyncSession, user_id: str, site_id: str, rows: list[Lead]) -> int:
    await lead_seen.remember(db, user_id, site_id, [r.identity_key for r in rows], SEEN_JUDGED)
    return await leads.delete_many(db, site_id, [r.id for r in rows])


async def screen_candidates(user_id: str, site_id: str, run_id: str) -> JobResult:
    async with unit_of_work() as db:
        run = await lead_runs.get(db, site_id, run_id)
        if run is None or run.status != "running":
            return {"status": "error", "error": "The run is no longer going."}, 0
        candidates = await leads.list_by_status(db, site_id, "candidate", MAX_CANDIDATES_PER_RUN)
        briefs = {b.id: b.text for b in await lead_briefs.list(db, site_id)}

    caller = Caller(user_id=user_id, site_id=site_id)
    gate = asyncio.Semaphore(SCREEN_CONCURRENCY)
    errors: list[str] = []

    async def decide(brief: str, batch: list[Lead]) -> list[tuple[Lead, bool]]:
        try:
            async with gate:
                result = await json_data_extractor.decide(
                    caller,
                    {"task": "find_leads_screen", "brief": brief},
                    {"brief": brief},
                    questions(batch),
                )
        except Exception as exc:
            errors.append(str(exc))
            return []
        answers = result["answers"]
        return [
            (lead, answers[f"p{seat}"]["choice"] == "yes")
            for seat, lead in enumerate(batch)
            if f"p{seat}" in answers
        ]

    planned = batches(candidates, briefs)
    verdicts = [
        v for done in await asyncio.gather(*(decide(b, rows) for b, rows in planned)) for v in done
    ]

    async with unit_of_work() as db:
        rows = await leads.get_many(db, site_id, [lead.id for lead, _ in verdicts])
        open_verdicts = [
            (rows[lead.id], keep)
            for lead, keep in verdicts
            if lead.id in rows and rows[lead.id].status == "candidate"
        ]
        kept = [row for row, keep in open_verdicts if keep]
        for row in kept:
            await leads.update(db, row, {"status": "shortlisted"})
        removed = await drop_leads(
            db, user_id, site_id, [row for row, keep in open_verdicts if not keep]
        )

    stats: dict[str, Any] = {
        "status": "error" if planned and len(errors) == len(planned) else "done",
        "total": len(candidates),
        "screened": len(verdicts),
        "kept": len(kept),
        "removed": removed,
    }
    if errors:
        stats["error"] = f"{len(errors)} of {len(planned)} batches failed: {errors[0]}"
    return stats, 0
