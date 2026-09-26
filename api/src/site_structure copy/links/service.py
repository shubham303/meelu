from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_structure.constants import SuggestionState
from src.site_structure.jobs import service as jobs
from src.site_structure.links.repository import link_suggestions
from src.site_structure.links.schemas import (
    LinkAction,
    LinkSuggestionCreateRequest,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    LinkSuggestionUpdateRequest,
    ReconcileResult,
)

NOT_FOUND = "No such link suggestion on this website."


class LinkSuggestionService:
    async def get(self, db: AsyncSession, site_id: str, suggestion_id: str) -> LinkSuggestionRecord:
        found = await link_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [found]))[0]

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        from_page_ids = (
            set(await site_pages.ids_by_url_substring(db, site_id, filters.from_url))
            if filters.from_url
            else None
        )
        to_page_ids = (
            set(await site_pages.ids_by_url_substring(db, site_id, filters.to_url))
            if filters.to_url
            else None
        )
        page = await link_suggestions.list(db, site_id, filters, paging, from_page_ids, to_page_ids)
        page.data = await self._with_pages(db, site_id, page.data)
        return page

    async def summary(self, db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
        return await link_suggestions.summary(db, site_id)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, body: LinkSuggestionCreateRequest
    ) -> LinkSuggestionRecord:
        await jobs.require(db, site_id, body.job_id)
        from_page_id = await self.resolve_page_id(
            db, site_id, body.from_page_id, body.from_url, "from"
        )
        to_page_id = await self.resolve_page_id(db, site_id, body.to_page_id, body.to_url, "to")
        if from_page_id == to_page_id:
            raise HTTPException(400, "A link cannot go from a page to itself.")
        if body.from_chunk_id:
            await self.require_chunk_on_page(db, site_id, body.from_chunk_id, from_page_id)
        linked = bool(
            await site_page_links.existing_pairs(db, site_id, [(from_page_id, to_page_id)])
        )
        if (
            body.action is LinkAction.CREATE
            and linked
            and body.state is not SuggestionState.USER_REJECTED
        ):
            raise HTTPException(409, "That link already exists on the site; nothing to add.")
        if body.action is LinkAction.DELETE and not linked:
            raise HTTPException(
                400, 'A "delete" suggestion needs a link the crawl found; there is none.'
            )
        clash = await link_suggestions.find_edge(db, site_id, from_page_id, to_page_id, body.action)
        if clash is not None:
            raise HTTPException(
                409,
                f'A "{body.action}" suggestion for that link already exists '
                f"({clash.id}, {clash.state}).",
            )
        created = await link_suggestions.create(
            db, user_id, site_id, body.to_new(from_page_id, to_page_id)
        )
        return (await self._with_pages(db, site_id, [created]))[0]

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        body: LinkSuggestionUpdateRequest,
    ) -> LinkSuggestionRecord:
        if body.from_chunk_id:
            current = await self.get(db, site_id, suggestion_id)
            await self.require_chunk_on_page(db, site_id, body.from_chunk_id, current.from_page_id)
        updated = await link_suggestions.update(db, site_id, suggestion_id, body.to_changes())
        if updated is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [updated]))[0]

    async def delete(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord:
        found = await self.get(db, site_id, suggestion_id)
        await link_suggestions.delete(db, site_id, found.id)
        return found

    async def reconcile(self, db: AsyncSession, site_id: str) -> ReconcileResult:
        open_rows = await link_suggestions.list_open(db, site_id)
        linked = await site_page_links.existing_pairs(
            db, site_id, [(r.from_page_id, r.to_page_id) for r in open_rows]
        )
        satisfied = {
            r.id
            for r in open_rows
            if (r.action is LinkAction.CREATE and (r.from_page_id, r.to_page_id) in linked)
            or (r.action is LinkAction.DELETE and (r.from_page_id, r.to_page_id) not in linked)
        }
        gone = await site_pages.gone_ids(db, site_id)
        page_gone = {
            r.id
            for r in open_rows
            if r.id not in satisfied and (r.from_page_id in gone or r.to_page_id in gone)
        }
        done = await link_suggestions.set_state(db, site_id, satisfied, SuggestionState.DONE)
        stale = await link_suggestions.set_state(db, site_id, page_gone, SuggestionState.STALE)
        return ReconcileResult(done=done, stale=stale)

    async def resolve_page_id(
        self, db: AsyncSession, site_id: str, page_id: str | None, url: str | None, end: str
    ) -> str:
        if page_id:
            if not await site_pages.exists(db, site_id, page_id):
                raise HTTPException(404, f"No page {page_id} on this website.")
            return page_id
        target = (url or "").strip()
        if not target:
            raise HTTPException(
                400, f"A suggestion needs a {end} page: send {end}PageId or {end}Url."
            )
        found = await site_pages.id_by_url(db, site_id, target)
        if not found:
            raise HTTPException(404, f"No page on record at {target}.")
        return found

    async def require_chunk_on_page(
        self, db: AsyncSession, site_id: str, chunk_id: str, page_id: str
    ) -> None:
        owner = await site_chunks.page_id_of(db, site_id, chunk_id)
        if owner is None:
            raise HTTPException(404, f"No chunk {chunk_id} on this website.")
        if owner != page_id:
            raise HTTPException(400, "The chunk must belong to the page the link goes from.")

    async def _with_pages(
        self, db: AsyncSession, site_id: str, records: list[LinkSuggestionRecord]
    ) -> list[LinkSuggestionRecord]:
        urls = await site_pages.urls_by_ids(
            db, site_id, [page_id for r in records for page_id in (r.from_page_id, r.to_page_id)]
        )
        chunk_ids = [r.from_chunk_id for r in records if r.from_chunk_id]
        chunks = {c.id: c for c in await site_chunks.list_by_ids(db, site_id, chunk_ids)}
        enriched = []
        for r in records:
            chunk = chunks.get(r.from_chunk_id) if r.from_chunk_id else None
            enriched.append(
                r.model_copy(
                    update={
                        "from_url": urls.get(r.from_page_id),
                        "to_url": urls.get(r.to_page_id),
                        "from_chunk_heading": chunk.heading_path if chunk else None,
                        "from_chunk_ordinal": chunk.ordinal if chunk else None,
                    }
                )
            )
        return enriched


link_suggestion_service = LinkSuggestionService()
