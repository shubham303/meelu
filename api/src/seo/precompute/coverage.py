from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.constants import CLUSTER_ATTACH_DISTANCE, CONTENT_TOP, LEXICAL_WEIGHT
from src.seo.repositories import (
    seo_keyword_clusters,
    seo_keyword_content_pages,
    seo_keyword_gsc_pages,
    seo_keywords,
    seo_page_facts,
    seo_site_states,
)
from src.seo.schemas import KeywordGscPageRecord, KeywordVector, PageFactsRecord
from src.site_pages.repositories.chunks import site_chunks


def lexical_hit(keyword: str, page: PageFactsRecord | None) -> bool:
    if page is None:
        return False
    return (
        keyword in (page.title or "").lower()
        or keyword in (page.h1 or "").lower()
        or any(keyword in h.lower() for h in page.headings)
    )


def blended_coverage(similarity: float | None, hit: bool) -> float:
    return min(1.0, (similarity or 0.0) * (1 - LEXICAL_WEIGHT) + (LEXICAL_WEIGHT if hit else 0.0))


def same_language(page: PageFactsRecord, language: str | None) -> bool:
    if page.lang is None:
        return True
    return language is not None and page.lang.split("-")[0] == language


class SeoCoverageService:
    async def refresh(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        keywords: list[KeywordVector],
        attach: bool,
    ) -> None:
        if not keywords:
            return
        started = datetime.now(UTC)
        state = await seo_site_states.get(db, site_id)
        language = state.language_code if state else None
        facts = {f.page_id: f for f in await seo_page_facts.list_for_site(db, site_id)}
        eligible = [
            page_id for page_id, f in facts.items() if f.live and same_language(f, language)
        ]
        pairs: dict[str, list[KeywordGscPageRecord]] = defaultdict(list)
        for pair in await seo_keyword_gsc_pages.list_for_keywords(
            db, site_id, [k.id for k in keywords]
        ):
            pairs[pair.keyword_id].append(pair)
        content_rows: list[dict[str, Any]] = []
        gsc_rows: list[dict[str, Any]] = []
        for keyword in keywords:
            best = await site_chunks.best_similarity_by_page(
                db, site_id, keyword.embedding, page_ids=eligible, limit=CONTENT_TOP
            )
            for page_id, similarity in best.items():
                hit = lexical_hit(keyword.keyword, facts.get(page_id))
                content_rows.append(
                    {
                        "keyword_id": keyword.id,
                        "page_id": page_id,
                        "coverage": blended_coverage(similarity, hit),
                        "lexical_hit": hit,
                    }
                )
            mine = pairs.get(keyword.id, [])
            if mine:
                similarities = await site_chunks.best_similarity_by_page(
                    db, site_id, keyword.embedding, page_ids=[p.page_id for p in mine]
                )
                for pair in mine:
                    hit = lexical_hit(keyword.keyword, facts.get(pair.page_id))
                    gsc_rows.append(
                        {
                            "id": pair.id,
                            "coverage": blended_coverage(similarities.get(pair.page_id), hit),
                            "lexical_hit": hit,
                        }
                    )
            if attach:
                cluster_id = await seo_keyword_clusters.nearest_id(
                    db, site_id, keyword.embedding, CLUSTER_ATTACH_DISTANCE
                )
                if cluster_id is not None:
                    await seo_keywords.set_cluster_if_unset(db, keyword.id, cluster_id)
        await seo_keyword_content_pages.upsert_many(db, user_id, site_id, content_rows, started)
        await seo_keyword_content_pages.prune_before(db, [k.id for k in keywords], started)
        await seo_keyword_gsc_pages.set_coverage_many(db, gsc_rows)


seo_coverage_service = SeoCoverageService()
