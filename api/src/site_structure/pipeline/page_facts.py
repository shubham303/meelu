from sqlalchemy.ext.asyncio import AsyncSession

from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_structure.pipeline.ranking import PageFacts, SiteDistribution, is_home


class PageFactsService:
    async def for_site(
        self, db: AsyncSession, site_id: str
    ) -> tuple[dict[str, PageFacts], SiteDistribution]:
        briefs = await site_pages.list_briefs(db, site_id)
        outlinks = await site_page_links.outlink_counts(db, site_id, region="body")
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id)
        pages = {
            b.id: PageFacts(
                page_id=b.id,
                inlinks=b.inlinks,
                outlinks=outlinks.get(b.id, 0),
                word_count=b.word_count,
                page_type=types.get(b.id),
                is_home=is_home(b.url),
            )
            for b in briefs
        }
        return pages, SiteDistribution.from_pages(list(pages.values()))

    async def for_pages(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, PageFacts]:
        briefs = await site_pages.list_by_ids(db, site_id, page_ids)
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, page_ids)
        return {
            b.id: PageFacts(
                page_id=b.id,
                inlinks=b.inlinks,
                outlinks=0,
                word_count=b.word_count,
                page_type=types.get(b.id),
                is_home=is_home(b.url),
            )
            for b in briefs
        }


page_facts_service = PageFactsService()
