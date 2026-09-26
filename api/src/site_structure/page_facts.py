from sqlalchemy.ext.asyncio import AsyncSession

from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_structure.hierarchy import is_home
from src.site_structure.ranking import PageFacts, SiteDistribution
from src.site_structure.repository import link_suggestions


class RankingFactsService:
    async def page_facts(
        self, db: AsyncSession, site_id: str
    ) -> tuple[dict[str, PageFacts], SiteDistribution]:
        briefs = await site_pages.list_briefs(db, site_id)
        outlinks = await site_page_links.outlink_counts(db, site_id, region="body")
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id)
        done = await link_suggestions.done_counts_by_from_page(db, site_id)
        pages = {
            b.id: PageFacts(
                page_id=b.id,
                inlinks=b.inlinks,
                outlinks=outlinks.get(b.id, 0),
                word_count=b.word_count,
                page_type=types.get(b.id),
                existing_suggestions=done.get(b.id, 0),
                is_home=is_home(b.url),
            )
            for b in briefs
        }
        return pages, SiteDistribution.from_pages(list(pages.values()))


ranking_facts_service = RankingFactsService()
