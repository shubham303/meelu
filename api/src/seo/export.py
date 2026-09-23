import csv
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.settings import settings

DATASETS = {
    "keywords": """
select k.keyword, k.volume, k.difficulty, k.cpc, k.intent, k.first_source, k.branded,
       k.our_position, k.our_url, k.impressions_28d, k.clicks_28d, k.impressions_prev_28d,
       k.clicks_prev_28d, hk.keyword as cluster_head
from seo_keywords k
left join seo_keyword_clusters c on c.id = k.cluster_id
left join seo_keywords hk on hk.id = c.head_keyword_id
where k.site_id = :site_id order by k.impressions_28d desc, k.volume desc nulls last
""",
    "gsc_pages": """
select k.keyword, f.url, g.position, g.impressions_28d, g.clicks_28d, g.impressions_prev_28d,
       g.clicks_prev_28d, g.ctr, g.ctr_gap, g.leader_days_90d, g.coverage, g.lexical_hit
from seo_keyword_gsc_pages g
join seo_keywords k on k.id = g.keyword_id
left join seo_page_facts f on f.page_id = g.page_id
where g.site_id = :site_id order by g.impressions_28d desc
""",
    "content_pages": """
select k.keyword, f.url, cp.coverage, cp.lexical_hit
from seo_keyword_content_pages cp
join seo_keywords k on k.id = cp.keyword_id
left join seo_page_facts f on f.page_id = cp.page_id
where cp.site_id = :site_id order by k.keyword, cp.coverage desc
""",
    "competitor_keywords": """
select cm.domain, k.keyword, ck.position, ck.url, ck.etv, k.volume, k.difficulty, k.intent
from seo_competitor_keywords ck
join seo_competitors cm on cm.id = ck.competitor_id
join seo_keywords k on k.id = ck.keyword_id
where ck.site_id = :site_id order by cm.domain, ck.position
""",
    "serps": """
select k.keyword, s.device, s.fetched_at, r.rank, r.domain, r.url, r.title, r.is_ours,
       array_to_string(s.features, '|') as features
from seo_serp_results r
join seo_serp_snapshots s on s.id = r.snapshot_id
join seo_keywords k on k.id = s.keyword_id
where s.site_id = :site_id order by k.keyword, s.fetched_at desc, r.rank
""",
    "suggestions": """
select s.id, s.action, s.state, s.topic_key, f.url as page_url, m.url as merge_into_url,
       array_to_string(s.strategies, '|') as strategies, s.suggestion, s.search_score,
       s.confidence, s.score, s.created_at
from seo_page_suggestions s
left join seo_page_facts f on f.page_id = s.page_id
left join seo_page_facts m on m.page_id = s.merge_into_page_id
where s.site_id = :site_id order by s.created_at desc
""",
}


async def write_csv(db: AsyncSession, site_id: str, schema: str, dataset: str) -> tuple[Path, int]:
    if dataset not in DATASETS:
        raise ValueError(f"Unknown dataset {dataset}. One of: {', '.join(DATASETS)}.")
    result = await db.execute(text(DATASETS[dataset]), {"site_id": site_id})
    columns = list(result.keys())
    out_dir = settings.agent_data_dir / "seo" / schema
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"{dataset}-{stamp}.csv"
    rows = 0
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(columns)
        for row in result:
            writer.writerow(list(row))
            rows += 1
    return path, rows
