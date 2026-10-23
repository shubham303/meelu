import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import credit_service
from src.find_leads.collect import (
    collect_linkedin_people,
    collect_post_authors,
    insert_fresh,
    normalize_keyword,
)
from src.find_leads.enrich import enrich_shortlist
from src.find_leads.identity import web_key
from src.find_leads.jobs import SILENT_ERROR, JobResult, is_silent, run_job, running_stats
from src.find_leads.models.brief import LeadBrief
from src.find_leads.models.run import LeadRun
from src.find_leads.repositories.briefs import lead_briefs
from src.find_leads.repositories.leads import leads
from src.find_leads.repositories.runs import lead_runs
from src.find_leads.repositories.searches import lead_searches
from src.find_leads.repositories.seen import lead_seen
from src.find_leads.schemas import (
    DEFAULT_SOURCES,
    KEYWORDS_PER_BRIEF,
    LEAD_STATUSES,
    LOOKBACK_DAYS,
    MAX_BRIEFS_PER_SITE,
    MAX_EVIDENCE,
    MAX_ROUNDS,
    MINIMUM_BALANCE_USD,
    RUN_STATUSES,
    SEARCH_RETENTION_DAYS,
    SEEN_DISCARDED,
    SEEN_JUDGED,
    SOURCES,
    USER_STATUSES,
    WEB_ANGLES_PER_BRIEF,
    WEB_PLATFORM,
    BriefCreateRequest,
    BriefPatchRequest,
    BriefResponse,
    BriefSearch,
    BriefUpsertItem,
    CandidatesRequest,
    CheckRequest,
    CheckResponse,
    InsertedResponse,
    JudgeRequest,
    LeadFilters,
    LeadPatchRequest,
    LeadResponse,
    RunCreateRequest,
    RunResponse,
    RunUpdateRequest,
    SearchResponse,
    SummaryResponse,
    UpsertResponse,
    VerdictResponse,
    WebSearchRecord,
)
from src.find_leads.screening import classify_leads, drop_leads, screen_candidates
from src.providers.people_search.service import people_search
from src.providers.social_search.service import social_search

QUIET_RUN_SECONDS = 120
QUIET_RUN_ERROR = "The app stopped working on this run before it finished, so it was closed."
SEEN_DAYS = 30
DISCARDED_DAYS = 30
BUSY = (
    "Another lead search is still going on one of your websites. "
    "Wait for it to finish or stop it first."
)
ENRICH_KEY = "enrich"
SCREEN_KEY = "screen"
TEXT_CHARS = 1000


class FindLeadsService:
    def __init__(self) -> None:
        self._jobs: set[asyncio.Task] = set()

    def _spawn(
        self, run_id: str, key: str, work: Callable[[], Awaitable[JobResult]], earlier: int
    ) -> None:
        task = asyncio.create_task(run_job(run_id, key, work, earlier))
        self._jobs.add(task)
        task.add_done_callback(self._jobs.discard)

    def _clean_text(self, text: str | None) -> str:
        clean = " ".join((text or "").split())
        if not clean:
            raise HTTPException(400, "Describe who you are looking for.")
        if len(clean) > TEXT_CHARS:
            raise HTTPException(400, f"A brief can be at most {TEXT_CHARS} characters.")
        return clean

    def _clean_sources(self, sources: list[str] | None) -> list[str]:
        chosen = list(dict.fromkeys(sources if sources is not None else DEFAULT_SOURCES))
        unknown = [s for s in chosen if s not in SOURCES]
        if unknown:
            raise HTTPException(400, f"Unknown source: {', '.join(unknown)}.")
        if not chosen:
            raise HTTPException(400, "Pick at least one place to look.")
        return chosen

    def _clean_keywords(self, values: list[str] | None) -> list[str]:
        keywords = list(dict.fromkeys(k for k in (normalize_keyword(k) for k in values or []) if k))
        if keywords and len(keywords) != KEYWORDS_PER_BRIEF:
            raise HTTPException(
                400, f"A brief needs exactly {KEYWORDS_PER_BRIEF} different keywords."
            )
        return keywords

    def _clean_angles(self, values: list[str] | None) -> list[str]:
        web = list(dict.fromkeys(" ".join(str(a).split()) for a in values or []))
        return [a for a in web if a][:WEB_ANGLES_PER_BRIEF]

    def _clean_plan(self, plan: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {"keywords": self._clean_keywords(plan.get("keywords"))}
        web = self._clean_angles(plan.get("web"))
        if web:
            out["web"] = web
        rounds = [
            {
                "keywords": self._clean_keywords(r.get("keywords")),
                "web": self._clean_angles(r.get("web")),
            }
            for r in (plan.get("rounds") or [])[: MAX_ROUNDS - 1]
        ]
        if rounds:
            out["rounds"] = rounds
        linkedin = plan.get("linkedin")
        if linkedin:
            query = " ".join(str(linkedin.get("query") or "").split())
            if query:
                out["linkedin"] = {
                    "query": query,
                    "titles": [t for t in (linkedin.get("titles") or []) if str(t).strip()][:5],
                    "locations": [
                        loc for loc in (linkedin.get("locations") or []) if str(loc).strip()
                    ][:5],
                }
        return out

    def _brief_response(
        self, row: LeadBrief, found: dict[str, int], kept: dict[str, int]
    ) -> BriefResponse:
        return BriefResponse(
            id=row.id,
            site_id=row.site_id,
            text=row.text,
            enabled=row.enabled,
            source=row.source,
            sources=row.sources,
            plan=row.plan or {},
            found=found.get(row.id, 0),
            kept=kept.get(row.id, 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _brief_counts(
        self, db: AsyncSession, site_id: str
    ) -> tuple[dict[str, int], dict[str, int]]:
        found = await leads.counts_by_brief(db, site_id)
        kept = await leads.counts_by_brief(db, site_id, USER_STATUSES)
        return found, kept

    async def list_briefs(self, db: AsyncSession, site_id: str) -> list[BriefResponse]:
        rows = await lead_briefs.list(db, site_id)
        found, kept = await self._brief_counts(db, site_id)
        return [self._brief_response(row, found, kept) for row in rows]

    async def _brief(self, db: AsyncSession, site_id: str, brief_id: str) -> LeadBrief:
        row = await lead_briefs.get(db, site_id, brief_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return row

    async def get_brief(self, db: AsyncSession, site_id: str, brief_id: str) -> BriefResponse:
        row = await self._brief(db, site_id, brief_id)
        found, kept = await self._brief_counts(db, site_id)
        return self._brief_response(row, found, kept)

    async def _require_room(self, db: AsyncSession, site_id: str, adding: int) -> None:
        if adding and await lead_briefs.count(db, site_id) + adding > MAX_BRIEFS_PER_SITE:
            raise HTTPException(
                400,
                f"A website can have at most {MAX_BRIEFS_PER_SITE} briefs. "
                "Remove or edit a brief before adding another.",
            )

    async def create_brief(
        self, db: AsyncSession, user_id: str, site_id: str, body: BriefCreateRequest
    ) -> BriefResponse:
        text = self._clean_text(body.text)
        if await lead_briefs.get_by_text(db, site_id, text) is not None:
            raise HTTPException(409, "That brief already exists.")
        await self._require_room(db, site_id, 1)
        row = await lead_briefs.create(
            db,
            user_id,
            site_id,
            {
                "text": text,
                "enabled": body.enabled,
                "source": "user",
                "sources": self._clean_sources(body.sources),
            },
        )
        return self._brief_response(row, {}, {})

    async def upsert_briefs(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[BriefUpsertItem]
    ) -> UpsertResponse:
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            text = self._clean_text(item.text)
            deduped[text] = {
                "text": text,
                "enabled": item.enabled,
                "source": item.source if item.source in ("user", "suggested") else "user",
                "sources": self._clean_sources(item.sources),
            }
        existing = await lead_briefs.existing_texts(db, site_id, list(deduped))
        added = len(deduped) - len(existing)
        await self._require_room(db, site_id, added)
        await lead_briefs.upsert_many(db, user_id, site_id, list(deduped.values()))
        return UpsertResponse(inserted=added, updated=len(existing))

    async def patch_brief(
        self, db: AsyncSession, site_id: str, brief_id: str, body: BriefPatchRequest
    ) -> BriefResponse:
        row = await self._brief(db, site_id, brief_id)
        values = body.changes()
        if "sources" in values:
            values["sources"] = self._clean_sources(values["sources"])
        if "plan" in values:
            values["plan"] = self._clean_plan(values["plan"] or {})
        if "text" in values:
            text = self._clean_text(values["text"])
            if text != row.text:
                other = await lead_briefs.get_by_text(db, site_id, text)
                if other is not None:
                    raise HTTPException(409, "That brief already exists.")
                values.update(text=text, plan={})
            else:
                values.pop("text")
        if "enabled" in values and values["enabled"] is None:
            values.pop("enabled")
        row = await lead_briefs.update(db, row, values)
        found, kept = await self._brief_counts(db, site_id)
        return self._brief_response(row, found, kept)

    async def delete_brief(self, db: AsyncSession, site_id: str, brief_id: str) -> str:
        await lead_briefs.delete(db, await self._brief(db, site_id, brief_id))
        return brief_id

    async def create_run(
        self, db: AsyncSession, user_id: str, site_id: str, body: RunCreateRequest
    ) -> RunResponse:
        await self._close_quiet_runs(db, user_id)
        if await lead_runs.running_for_user(db, user_id) is not None:
            raise HTTPException(409, BUSY)
        balance = await credit_service.balance(db, user_id)
        if balance.balance_micros < MINIMUM_BALANCE_USD * 1_000_000:
            raise HTTPException(
                402, f"Finding leads needs a credit balance of at least ${MINIMUM_BALANCE_USD}."
            )
        if not await lead_briefs.list_enabled(db, site_id):
            raise HTTPException(400, "Add a brief describing who you are looking for first.")
        try:
            async with db.begin_nested():
                return await lead_runs.create(db, user_id, site_id, body.target_count)
        except IntegrityError:
            raise HTTPException(409, BUSY) from None

    async def _close_quiet_runs(self, db: AsyncSession, user_id: str) -> None:
        await lead_runs.fail_quiet_since(
            db,
            datetime.now(UTC) - timedelta(seconds=QUIET_RUN_SECONDS),
            QUIET_RUN_ERROR,
            user_id=user_id,
        )

    async def _running_run(self, db: AsyncSession, site_id: str, run_id: str) -> LeadRun:
        row = await lead_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        if row.status != "running":
            raise HTTPException(409, "This run is no longer going.")
        return await self._close_silent_jobs(db, row)

    async def _start_job(
        self,
        db: AsyncSession,
        site_id: str,
        run_id: str,
        key: str,
        work: Callable[[], Awaitable[JobResult]],
    ) -> RunResponse:
        row = await self._running_run(db, site_id, run_id)
        previous = row.source_stats.get(key) or {}
        if previous.get("status") == "running":
            return RunResponse.model_validate(row)
        earlier = int(previous.get("candidates") or 0)
        await lead_runs.merge_source_stats(db, run_id, key, running_stats(earlier))
        await db.commit()
        self._spawn(run_id, key, work, earlier)
        row = await lead_runs.get(db, site_id, run_id)
        await db.refresh(row)
        return RunResponse.model_validate(row)

    async def start_collect(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        run_id: str,
        source: str,
        platform: str | None,
        searches: list[BriefSearch] | None = None,
    ) -> RunResponse:
        await self._running_run(db, site_id, run_id)
        keywords = None if searches is None else {s.brief_id: s.keywords for s in searches}
        if source == "posts":
            if not platform or not social_search.supports(f"search.{platform}"):
                raise HTTPException(400, f"{platform or 'That platform'} cannot be searched now.")
            return await self._start_job(
                db,
                site_id,
                run_id,
                f"posts:{platform}",
                lambda: collect_post_authors(user_id, site_id, run_id, platform, keywords),
            )
        if source == "linkedin":
            if not people_search.supports("search.linkedin"):
                raise HTTPException(400, "LinkedIn people search is not available right now.")
            return await self._start_job(
                db,
                site_id,
                run_id,
                "linkedin",
                lambda: collect_linkedin_people(user_id, site_id, run_id),
            )
        raise HTTPException(400, "source must be posts or linkedin; the app sends web leads.")

    async def start_screen(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str
    ) -> RunResponse:
        return await self._start_job(
            db,
            site_id,
            run_id,
            SCREEN_KEY,
            lambda: screen_candidates(user_id, site_id, run_id),
        )

    async def start_enrich(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str
    ) -> RunResponse:
        return await self._start_job(
            db,
            site_id,
            run_id,
            ENRICH_KEY,
            lambda: enrich_shortlist(user_id, site_id, run_id),
        )

    async def patch_run(
        self, db: AsyncSession, site_id: str, run_id: str, body: RunUpdateRequest
    ) -> RunResponse:
        row = await lead_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        status = values.get("status")
        if status is not None and status not in RUN_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(RUN_STATUSES)}.")
        if status in ("done", "stopped", "error"):
            values["finished_at"] = datetime.now(UTC)
        return await lead_runs.update(db, row, values)

    async def list_runs(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        return await lead_runs.list(db, site_id, paging)

    async def get_run(self, db: AsyncSession, site_id: str, run_id: str) -> RunResponse:
        row = await lead_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return RunResponse.model_validate(await self._close_silent_jobs(db, row))

    async def _close_silent_jobs(self, db: AsyncSession, row: LeadRun) -> LeadRun:
        now = datetime.now(UTC)
        silent = [k for k, stats in row.source_stats.items() if is_silent(stats or {}, now)]
        for key in silent:
            await lead_runs.merge_source_stats(
                db, row.id, key, {"status": "error", "error": SILENT_ERROR}
            )
        if silent:
            await db.refresh(row)
        return row

    async def add_candidates(
        self, db: AsyncSession, user_id: str, site_id: str, body: CandidatesRequest
    ) -> InsertedResponse:
        run = await self._running_run(db, site_id, body.run_id)
        briefs = {b.id for b in await lead_briefs.list(db, site_id)}
        rows = []
        for item in body.leads:
            email = (item.email or "").strip().lower() or None
            if email and not item.email_source_url:
                email = None
            key = web_key(email, item.website, item.profile_url)
            if key is None:
                continue
            rows.append(
                {
                    "identity_key": key,
                    "source": "web",
                    "platform": "web",
                    "brief_id": item.brief_id if item.brief_id in briefs else None,
                    "name": item.name,
                    "headline": item.headline,
                    "website": item.website,
                    "profile_url": item.profile_url,
                    "email": email,
                    "email_source_url": item.email_source_url if email else None,
                    "snippet": item.snippet,
                    "evidence": [e.model_dump() for e in item.evidence][:MAX_EVIDENCE],
                }
            )
        inserted, skipped = await insert_fresh(db, user_id, site_id, run.id, rows)
        previous = run.source_stats.get("web") or {}
        await lead_runs.merge_source_stats(
            db,
            run.id,
            "web",
            {
                "status": "done",
                "candidates": int(previous.get("candidates") or 0) + inserted,
                "skipped": int(previous.get("skipped") or 0) + skipped,
            },
            found=inserted,
        )
        return InsertedResponse(inserted=inserted, skipped=skipped)

    async def judge(
        self, db: AsyncSession, user_id: str, site_id: str, body: JudgeRequest
    ) -> VerdictResponse:
        rows = await leads.get_many(db, site_id, [v.id for v in body.leads])
        kept, dropped = 0, []
        for verdict in body.leads:
            row = rows.get(verdict.id)
            if row is None:
                raise HTTPException(404, f"No lead {verdict.id} for this website.")
            if row.status != "shortlisted":
                continue
            if not verdict.keep:
                dropped.append(row)
                continue
            known = {e.get("url") for e in [*(row.evidence or []), *(row.activity or [])]}
            chosen = [e.model_dump() for e in verdict.evidence if e.url in known][:MAX_EVIDENCE]
            await leads.update(
                db,
                row,
                {
                    "status": "new",
                    "reason": verdict.reason,
                    "angle": verdict.angle,
                    "evidence": chosen or (row.evidence or [])[:MAX_EVIDENCE],
                },
            )
            kept += 1
        return VerdictResponse(kept=kept, removed=await drop_leads(db, user_id, site_id, dropped))

    async def check(
        self, db: AsyncSession, user_id: str, site_id: str, body: CheckRequest
    ) -> CheckResponse:
        rows = await leads.get_many(db, site_id, body.ids)
        shortlisted = [rows[i] for i in body.ids if i in rows and rows[i].status == "shortlisted"]
        briefs = {b.id: b.text for b in await lead_briefs.list(db, site_id)}
        await db.commit()
        verdicts, errors, planned = await classify_leads(
            user_id, site_id, shortlisted, briefs, "find_leads_check", with_activity=True
        )
        if planned and len(errors) == planned:
            raise HTTPException(502, f"The fit check failed: {errors[0]}")
        fresh = await leads.get_many(db, site_id, [lead.id for lead, _ in verdicts])
        open_verdicts = [
            (fresh[lead.id], keep)
            for lead, keep in verdicts
            if lead.id in fresh and fresh[lead.id].status == "shortlisted"
        ]
        removed = await drop_leads(
            db, user_id, site_id, [row for row, keep in open_verdicts if not keep]
        )
        return CheckResponse(fits=[row.id for row, keep in open_verdicts if keep], removed=removed)

    async def list_searches(
        self, db: AsyncSession, site_id: str, platform: str
    ) -> list[SearchResponse]:
        rows = await lead_searches.by_query(db, site_id, platform)
        return [SearchResponse.model_validate(row) for row in rows.values()]

    async def record_web_search(
        self, db: AsyncSession, user_id: str, site_id: str, body: WebSearchRecord
    ) -> SearchResponse:
        query = " ".join(body.query.split())
        if not query:
            raise HTTPException(400, "query must not be empty.")
        await lead_searches.record(
            db,
            user_id,
            site_id,
            WEB_PLATFORM,
            [{"query": query, "results": body.results}],
            datetime.now(UTC),
        )
        row = (await lead_searches.by_query(db, site_id, WEB_PLATFORM, [query]))[query]
        await db.refresh(row)
        return SearchResponse.model_validate(row)

    async def list_leads(
        self, db: AsyncSession, site_id: str, filters: LeadFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[LeadResponse]:
        for status in filters.statuses or []:
            if status not in LEAD_STATUSES:
                raise HTTPException(400, f"status must be one of {', '.join(LEAD_STATUSES)}.")
        return await leads.list(db, site_id, filters, paging)

    async def get_lead(self, db: AsyncSession, site_id: str, lead_id: str) -> LeadResponse:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return LeadResponse.model_validate(row)

    async def patch_lead(
        self, db: AsyncSession, site_id: str, lead_id: str, body: LeadPatchRequest
    ) -> LeadResponse:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        status = body.changes().get("status")
        if status is None:
            return LeadResponse.model_validate(row)
        if status not in USER_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(USER_STATUSES)}.")
        if row.status not in USER_STATUSES:
            raise HTTPException(409, "This lead was never shown for review.")
        now = datetime.now(UTC)
        values: dict[str, Any] = {
            "status": status,
            "contacted_at": now if status == "contacted" else None,
            "discarded_at": now if status == "discarded" else None,
        }
        if status == row.status:
            values.pop("contacted_at")
            values.pop("discarded_at")
        return LeadResponse.model_validate(await leads.update(db, row, values))

    async def delete_lead(self, db: AsyncSession, user_id: str, site_id: str, lead_id: str) -> str:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        await lead_seen.remember(db, user_id, site_id, [row.identity_key], SEEN_DISCARDED)
        await leads.delete_many(db, site_id, [row.id])
        return lead_id

    async def summary(self, db: AsyncSession, user_id: str, site_id: str) -> SummaryResponse:
        await self._close_quiet_runs(db, user_id)
        statuses = await leads.status_counts(db, site_id)
        return SummaryResponse(
            new=statuses.get("new", 0),
            contacted=statuses.get("contacted", 0),
            discarded=statuses.get("discarded", 0),
            unprocessed=statuses.get("candidate", 0) + statuses.get("shortlisted", 0),
            last_run=await lead_runs.latest(db, site_id),
        )

    async def purge(self, db: AsyncSession) -> dict[str, int]:
        now = datetime.now(UTC)
        expired = await leads.discarded_before(db, now - timedelta(days=DISCARDED_DAYS))
        by_site: dict[tuple[str, str], list[str]] = {}
        for row in expired:
            by_site.setdefault((row.user_id, row.site_id), []).append(row.identity_key)
        for (user_id, site_id), keys in by_site.items():
            await lead_seen.remember(db, user_id, site_id, keys, SEEN_DISCARDED)
        return {
            "discarded": await leads.delete_ids(db, [r.id for r in expired]),
            "pipeline": await leads.delete_pipeline_before(db, now - timedelta(days=LOOKBACK_DAYS)),
            "seen": await lead_seen.delete_kind_before(
                db, SEEN_JUDGED, now - timedelta(days=SEEN_DAYS)
            ),
            "runs": await lead_runs.fail_quiet_since(
                db, now - timedelta(seconds=QUIET_RUN_SECONDS), QUIET_RUN_ERROR
            ),
            "searches": await lead_searches.delete_older_than(
                db, now - timedelta(days=SEARCH_RETENTION_DAYS)
            ),
        }


find_leads_service = FindLeadsService()
