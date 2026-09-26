import csv
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.repositories import (
    seo_competitor_keywords,
    seo_competitors,
    seo_keyword_clusters,
    seo_keyword_content_pages,
    seo_keyword_gsc_pages,
    seo_keywords,
    seo_page_facts,
    seo_page_suggestions,
    seo_serp_results,
    seo_serp_snapshots,
)
from src.seo.schemas import KeywordRecord
from src.settings import settings

DATASETS = ("keywords", "gsc_pages", "content_pages", "competitor_keywords", "serps", "suggestions")

Table = tuple[list[str], list[tuple]]


class SeoExportService:
    async def write_csv(
        self, db: AsyncSession, site_id: str, schema: str, dataset: str
    ) -> tuple[Path, int]:
        if dataset not in DATASETS:
            raise ValueError(f"Unknown dataset {dataset}. One of: {', '.join(DATASETS)}.")
        columns, rows = await getattr(self, dataset)(db, site_id)
        out_dir = settings.agent_data_dir / "seo" / schema
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        path = out_dir / f"{dataset}-{stamp}.csv"
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(columns)
            for row in rows:
                writer.writerow(list(row))
        return path, len(rows)

    async def _keywords_by_id(self, db: AsyncSession, site_id: str) -> dict[str, KeywordRecord]:
        return {k.id: k for k in await seo_keywords.list_for_site(db, site_id)}

    async def _page_urls(self, db: AsyncSession, site_id: str) -> dict[str, str]:
        return {f.page_id: f.url for f in await seo_page_facts.list_for_site(db, site_id)}

    async def keywords(self, db: AsyncSession, site_id: str) -> Table:
        keywords = await seo_keywords.list_for_site(db, site_id)
        clusters = await seo_keyword_clusters.list_by_ids(
            db, site_id, list({k.cluster_id for k in keywords if k.cluster_id})
        )
        names = {k.id: k.keyword for k in keywords}
        heads = {c.id: names.get(c.head_keyword_id) for c in clusters}
        columns = [
            "keyword",
            "volume",
            "difficulty",
            "cpc",
            "intent",
            "first_source",
            "branded",
            "our_position",
            "our_url",
            "impressions_28d",
            "clicks_28d",
            "impressions_prev_28d",
            "clicks_prev_28d",
            "cluster_head",
        ]
        rows = [
            (
                k.keyword,
                k.volume,
                k.difficulty,
                k.cpc,
                k.intent,
                k.first_source,
                k.branded,
                k.our_position,
                k.our_url,
                k.impressions_28d,
                k.clicks_28d,
                k.impressions_prev_28d,
                k.clicks_prev_28d,
                heads.get(k.cluster_id) if k.cluster_id else None,
            )
            for k in keywords
        ]
        return columns, rows

    async def gsc_pages(self, db: AsyncSession, site_id: str) -> Table:
        keywords = await self._keywords_by_id(db, site_id)
        urls = await self._page_urls(db, site_id)
        columns = [
            "keyword",
            "url",
            "position",
            "impressions_28d",
            "clicks_28d",
            "impressions_prev_28d",
            "clicks_prev_28d",
            "ctr",
            "ctr_gap",
            "leader_days_90d",
            "coverage",
            "lexical_hit",
        ]
        rows = [
            (
                keywords[g.keyword_id].keyword,
                urls.get(g.page_id),
                g.position,
                g.impressions_28d,
                g.clicks_28d,
                g.impressions_prev_28d,
                g.clicks_prev_28d,
                g.ctr,
                g.ctr_gap,
                g.leader_days_90d,
                g.coverage,
                g.lexical_hit,
            )
            for g in await seo_keyword_gsc_pages.list_for_site(db, site_id)
            if g.keyword_id in keywords
        ]
        return columns, rows

    async def content_pages(self, db: AsyncSession, site_id: str) -> Table:
        keywords = await self._keywords_by_id(db, site_id)
        urls = await self._page_urls(db, site_id)
        found = [
            c
            for c in await seo_keyword_content_pages.list_for_site(db, site_id)
            if c.keyword_id in keywords
        ]
        found.sort(key=lambda c: (keywords[c.keyword_id].keyword, -c.coverage))
        rows = [
            (keywords[c.keyword_id].keyword, urls.get(c.page_id), c.coverage, c.lexical_hit)
            for c in found
        ]
        return ["keyword", "url", "coverage", "lexical_hit"], rows

    async def competitor_keywords(self, db: AsyncSession, site_id: str) -> Table:
        keywords = await self._keywords_by_id(db, site_id)
        domains = {c.id: c.domain for c in await seo_competitors.list(db, site_id, None)}
        found = [
            r
            for r in await seo_competitor_keywords.list_for_site(db, site_id)
            if r.competitor_id in domains and r.keyword_id in keywords
        ]
        found.sort(key=lambda r: (domains[r.competitor_id], r.position is None, r.position or 0))
        columns = [
            "domain",
            "keyword",
            "position",
            "url",
            "etv",
            "volume",
            "difficulty",
            "intent",
        ]
        rows = [
            (
                domains[r.competitor_id],
                keywords[r.keyword_id].keyword,
                r.position,
                r.url,
                r.etv,
                keywords[r.keyword_id].volume,
                keywords[r.keyword_id].difficulty,
                keywords[r.keyword_id].intent,
            )
            for r in found
        ]
        return columns, rows

    async def serps(self, db: AsyncSession, site_id: str) -> Table:
        keywords = await self._keywords_by_id(db, site_id)
        snapshots = {
            s.id: s
            for s in await seo_serp_snapshots.list_for_site(db, site_id)
            if s.keyword_id in keywords
        }
        results = await seo_serp_results.list_by_snapshot_ids(db, list(snapshots))
        joined = [(snapshots[r.snapshot_id], r) for r in results]
        joined.sort(
            key=lambda sr: (
                keywords[sr[0].keyword_id].keyword,
                -sr[0].fetched_at.timestamp(),
                sr[1].rank,
            )
        )
        columns = [
            "keyword",
            "device",
            "fetched_at",
            "rank",
            "domain",
            "url",
            "title",
            "is_ours",
            "features",
        ]
        rows = [
            (
                keywords[s.keyword_id].keyword,
                s.device,
                s.fetched_at,
                r.rank,
                r.domain,
                r.url,
                r.title,
                r.is_ours,
                "|".join(s.features),
            )
            for s, r in joined
        ]
        return columns, rows

    async def suggestions(self, db: AsyncSession, site_id: str) -> Table:
        urls = await self._page_urls(db, site_id)
        columns = [
            "id",
            "action",
            "state",
            "topic_key",
            "page_url",
            "merge_into_url",
            "strategies",
            "suggestion",
            "search_score",
            "confidence",
            "score",
            "created_at",
        ]
        rows = [
            (
                s.id,
                s.action,
                s.state,
                s.topic_key,
                urls.get(s.page_id) if s.page_id else None,
                urls.get(s.merge_into_page_id) if s.merge_into_page_id else None,
                "|".join(s.strategies),
                s.suggestion,
                s.search_score,
                s.confidence,
                s.score,
                s.created_at,
            )
            for s in await seo_page_suggestions.list_for_site(db, site_id)
        ]
        return columns, rows


seo_export_service = SeoExportService()
