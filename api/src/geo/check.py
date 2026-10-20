import asyncio
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.credits.service import InsufficientCreditsError
from src.embed_worker.search.service import page_search_service
from src.geo.prompts import (
    ADVICE,
    COMPARE,
    COMPARE_SCHEMA,
    JUDGE_PAGE,
    JUDGE_PAGE_SCHEMA,
    UNDERSTAND,
    UNDERSTAND_SCHEMA,
)
from src.geo.repositories.checks import geo_checks
from src.geo.repositories.queries import geo_queries
from src.geo.schemas import CANDIDATE_PAGES, GOOD_POSITION, INTENTS, POINT_STATUSES
from src.providers.errors import ProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo.market import location_code
from src.seo.site_search.repositories.site_search_daily import site_search_dailies, strip_slash
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas.llm_extraction import PendingPageRecord
from src.sites.repository import sites

log = get_logger()

POINT_WEIGHT = {"answers": 1.0, "partly": 0.5, "missing": 0.0}


class CheckAborted(Exception):
    pass


def page_data(page: PendingPageRecord) -> dict[str, Any]:
    return {
        "url": page.url,
        "title": page.title,
        "h1": page.h1,
        "metaDescription": page.meta_description,
        "body": page.body_text or "",
    }


def clean_points(raw: Any) -> list[str]:
    seen: dict[str, None] = {}
    for item in raw or []:
        point = " ".join(str(item or "").split())
        if point:
            seen[point] = None
    return list(seen)


def judged_points(points: list[str], raw: Any) -> list[dict[str, Any]]:
    by_text = {" ".join(str((r or {}).get("point") or "").split()): r for r in raw or [] if r}
    ordered = list(raw or [])
    out = []
    for i, point in enumerate(points):
        found = by_text.get(point) or (ordered[i] if i < len(ordered) else None) or {}
        status = found.get("status") if found.get("status") in POINT_STATUSES else "missing"
        evidence = str(found.get("evidence") or "").strip()
        out.append(
            {
                "point": point,
                "status": status,
                "evidence": evidence if status != "missing" and evidence else None,
            }
        )
    return out


def coverage(points: list[dict[str, Any]]) -> float:
    if not points:
        return 0.0
    return round(sum(POINT_WEIGHT[p["status"]] for p in points) / len(points), 3)


def verdict_of(best: dict[str, Any] | None, position: float | None) -> str:
    if best is None or all(p["status"] == "missing" for p in best["points"]):
        return "no_page"
    if any(p["status"] != "answers" for p in best["points"]):
        return "partial"
    if position is not None and position <= GOOD_POSITION:
        return "covered"
    return "low_rank"


def host_of(url: str) -> str:
    return own_domain(urlparse(url).netloc)


def cites(citations: list[dict[str, Any]], domain: str) -> bool:
    if not domain:
        return False
    for c in citations:
        host = host_of(c.get("url") or "")
        if host == domain or host.endswith("." + domain):
            return True
    return False


class Progress:
    def __init__(self, check_id: str) -> None:
        self.check_id = check_id
        self.values: dict[str, Any] = {"pages_judged": 0, "answers_fetched": 0}
        self.lock = asyncio.Lock()

    async def set(self, **values: Any) -> None:
        async with self.lock:
            self.values.update(values)
            await self.save()

    async def bump(self, key: str) -> None:
        async with self.lock:
            self.values[key] += 1
            await self.save()

    async def save(self) -> None:
        async with unit_of_work() as db:
            await geo_checks.update(db, self.check_id, {"progress": dict(self.values)})


class GeoChecker:
    async def run(self, user_id: str, site_id: str, check_id: str) -> None:
        caller = Caller(user_id=user_id, site_id=site_id)
        try:
            values = await self.evaluate(caller, check_id)
            values.update(status="done", error=None)
        except (CheckAborted, ProviderError, InsufficientCreditsError) as exc:
            values = {"status": "error", "error": str(exc)}
        except Exception as exc:
            log.exception("geo.check.crashed", check_id=check_id)
            values = {"status": "error", "error": f"The check failed: {exc}"}
        values["finished_at"] = datetime.now(UTC)
        async with unit_of_work() as db:
            await geo_checks.finish_running(db, check_id, values)

    async def evaluate(self, caller: Caller, check_id: str) -> dict[str, Any]:
        site_id = caller.site_id
        assert site_id is not None
        progress = Progress(check_id)
        await progress.set(stage="pages")
        async with unit_of_work() as db:
            check = await geo_checks.get(db, site_id, check_id)
            if check is None:
                raise CheckAborted("The check no longer exists.")
            query = await geo_queries.get(db, site_id, check.query_id)
            if query is None:
                raise CheckAborted("The question was removed.")
            site = await sites.get(db, caller.user_id, site_id)
            if site is None:
                raise CheckAborted("The website was removed.")
            question = query.text
            domain = own_domain(site.domain)
            country = (site.markets or [None])[0]
            found = await page_search_service.search_from_query(
                db, site_id, question, limit=CANDIDATE_PAGES
            )
            order = [h.page_id for h in found.hits]
            records = {p.id: p for p in await site_pages.pending_records_by_ids(db, site_id, order)}
            candidates = [records[i] for i in order if i in records and records[i].body_text]

        await progress.set(stage="question", pages_found=len(candidates))
        understood = await self.understand(caller, question)
        intent = understood["intent"]
        points = understood["points"]
        await progress.set(stage="judge", points=len(points))

        async def judge_one(page: PendingPageRecord) -> list[dict[str, Any]]:
            judged_page = await self.judge(caller, question, intent, points, page)
            await progress.bump("pages_judged")
            return judged_page

        judged, answers = await asyncio.gather(
            asyncio.gather(*(judge_one(p) for p in candidates)),
            self.ai_answers(caller, question, country, site.language, progress),
        )
        pages = sorted(
            (
                {
                    "pageId": page.id,
                    "url": page.url,
                    "title": page.title,
                    "coverage": coverage(page_points),
                    "points": page_points,
                }
                for page, page_points in zip(candidates, judged, strict=True)
            ),
            key=lambda p: -p["coverage"],
        )
        best = pages[0] if pages and pages[0]["coverage"] > 0 else None
        best_page = next((p for p in candidates if best and p.id == best["pageId"]), None)

        position = None
        if best is not None:
            async with unit_of_work() as db:
                positions = await site_search_dailies.page_positions(db, site_id, [best["url"]])
            hit = positions.get(strip_slash(best["url"]))
            position = round(hit[0], 1) if hit else None

        verdict = verdict_of(best, position)
        await progress.set(stage="compare")
        compared = await self.compare(
            caller, question, intent, points, best_page, position, verdict, answers
        )
        by_platform = {a.get("platform"): a for a in compared.get("answers") or [] if a}
        for answer in answers:
            judged_answer = by_platform.get(answer["platform"]) or {}
            answer["covers"] = clean_points(judged_answer.get("covers"))
            answer["misses"] = clean_points(judged_answer.get("misses"))
            answer["citedUs"] = cites(answer["citations"], domain)

        return {
            "intent": intent,
            "required_points": points,
            "verdict": verdict,
            "page_id": best["pageId"] if best else None,
            "page_url": best["url"] if best else None,
            "position": position,
            "pages": pages,
            "ai_answers": answers,
            "page_adds": clean_points(compared.get("pageAdds")) if best else [],
            "suggestion": str(compared.get("suggestion") or "").strip() or ADVICE[verdict],
            "model": compared.get("model"),
        }

    async def understand(self, caller: Caller, question: str) -> dict[str, Any]:
        result = await json_data_extractor.extract(
            caller, {"geo": "understand"}, UNDERSTAND, {"question": question}, UNDERSTAND_SCHEMA
        )
        body = result.get("result") or {}
        intent = body.get("intent") if body.get("intent") in INTENTS else "informational"
        points = clean_points(body.get("points"))
        if not points:
            raise CheckAborted("The model could not tell what the question asks for.")
        return {"intent": intent, "points": points}

    async def judge(
        self,
        caller: Caller,
        question: str,
        intent: str,
        points: list[str],
        page: PendingPageRecord,
    ) -> list[dict[str, Any]]:
        result = await json_data_extractor.extract(
            caller,
            {"geo": "judge", "pageId": page.id, "contentHash": page.content_hash},
            JUDGE_PAGE,
            {"question": question, "intent": intent, "points": points, "page": page_data(page)},
            JUDGE_PAGE_SCHEMA,
        )
        return judged_points(points, (result.get("result") or {}).get("points"))

    async def ai_answers(
        self,
        caller: Caller,
        question: str,
        country: str | None,
        language: str | None,
        progress: Progress,
    ) -> list[dict[str, Any]]:
        location = None
        if country:
            try:
                location = location_code(country)
            except (AttributeError, LookupError, ValueError):
                location = None

        async def fetch(platform: str) -> dict[str, Any]:
            if platform == "ai_overview":
                return await seo_data.ai_overview(caller, question, location, language)
            return {"shown": True, **await seo_data.ai_answer(caller, platform, question, country)}

        async def one(platform: str) -> dict[str, Any]:
            answer = await attempt(platform)
            await progress.bump("answers_fetched")
            return answer

        async def attempt(platform: str) -> dict[str, Any]:
            try:
                try:
                    got = await fetch(platform)
                except ProviderRequestError:
                    got = await fetch(platform)
            except InsufficientCreditsError:
                raise
            except ProviderError as exc:
                return {
                    "platform": platform,
                    "shown": False,
                    "text": "",
                    "citations": [],
                    "error": str(exc),
                }
            shown = bool(got.get("shown")) and bool(got.get("text"))
            return {
                "platform": platform,
                "shown": shown,
                "text": got.get("text") or "",
                "citations": got.get("citations") or [],
                "error": None,
            }

        return list(await asyncio.gather(*(one(p) for p in ("chat_gpt", "claude", "ai_overview"))))

    async def compare(
        self,
        caller: Caller,
        question: str,
        intent: str,
        points: list[str],
        page: PendingPageRecord | None,
        position: float | None,
        verdict: str,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = {
            "question": question,
            "intent": intent,
            "points": points,
            "page": page_data(page) if page is not None else None,
            "position": position,
            "verdict": verdict,
            "advice": ADVICE[verdict],
            "answers": [
                {"platform": a["platform"], "text": a["text"]} for a in answers if a["shown"]
            ],
        }
        result = await json_data_extractor.extract(
            caller, {"geo": "compare"}, COMPARE, data, COMPARE_SCHEMA
        )
        return {**(result.get("result") or {}), "model": result.get("model")}


geo_checker = GeoChecker()
