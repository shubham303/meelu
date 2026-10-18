import asyncio
import sys

from src.core.database import unit_of_work
from src.embed_worker.chunking import chunk_body, page_chunk
from src.embed_worker.embedding import passage_input, post_input, query_input
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageChunkSource
from src.social_listening.repositories.queries import social_listening_queries
from src.providers.social_search.repository import social_posts

MAX_EMBED_ATTEMPTS = 3
MAX_ERROR_CHARS = 500


class EmbedWorkerService:
    async def run_chunk_pass(self, page_batch: int) -> tuple[int, int]:
        async with unit_of_work() as db:
            await self._prune_unserved_chunks(db)
        pages = chunks = 0
        failed: list[str] = []
        for _ in range(page_batch):
            page = None
            try:
                async with unit_of_work() as db:
                    claimed = await site_pages.claim_needing_chunks(db, 1, tuple(failed))
                    if not claimed:
                        break
                    page = claimed[0]
                    anchors = await site_page_links.inbound_anchors_by_page_ids(db, [page.id])
                    chunks += await self._rechunk_page(db, page, anchors.get(page.id, []))
                    pages += 1
            except Exception as e:
                if page is None:
                    raise
                failed.append(page.id)
                print(f"embed-worker: could not chunk {page.url} — {e}", file=sys.stderr)
        return pages, chunks

    async def run_embed_pass(
        self, embedder, model: str, batch: int = 32, max_batches: int = 4
    ) -> int:
        done = 0
        for _ in range(max_batches):
            async with unit_of_work() as db:
                rows = await site_chunks.claim_pending_embeddings(db, MAX_EMBED_ATTEMPTS, batch)
                if not rows:
                    break
                titles = {
                    p.id: p.title
                    for p in await site_pages.list_by_ids(db, None, [r.page_id for r in rows])
                }
                inputs = [
                    passage_input(titles.get(r.page_id), r.heading_path, r.text) for r in rows
                ]
                try:
                    vectors = await asyncio.to_thread(embedder.embed, inputs)
                except Exception as e:
                    for r in rows:
                        await self._mark_chunk_failed(db, r.id, str(e))
                    continue
                for row, vector in zip(rows, vectors):
                    await site_chunks.write_embedding(db, row.id, row.from_hash, vector, model)
                touched = {row.page_id for row in rows}
                incomplete = await site_chunks.page_ids_with_unembedded(db, list(touched))
                await site_pages.clear_embed_state(db, list(touched - incomplete))
                done += len(rows)
        return done

    async def run_listening_pass(self, embedder, model: str, batch: int, max_batches: int) -> int:
        done = 0
        for repository, to_input in (
            (social_listening_queries, lambda r: query_input(r.text)),
            (social_posts, lambda r: post_input(r.title, r.text)),
        ):
            for _ in range(max_batches):
                async with unit_of_work() as db:
                    rows = await repository.claim_pending_embeddings(db, MAX_EMBED_ATTEMPTS, batch)
                    if not rows:
                        break
                    try:
                        vectors = await asyncio.to_thread(
                            embedder.embed, [to_input(r) for r in rows]
                        )
                    except Exception as e:
                        for r in rows:
                            await repository.mark_embed_failed(db, r.id, str(e)[:MAX_ERROR_CHARS])
                        continue
                    for row, vector in zip(rows, vectors):
                        await repository.write_embedding(db, row.id, vector, model)
                    done += len(rows)
        return done

    async def _rechunk_page(self, db, page: SitePageChunkSource, inbound_anchors: list[str]) -> int:
        source = {
            "title": page.title,
            "h1": page.h1,
            "meta_description": page.meta_description,
            "body_text": page.body_text,
            "inbound_anchors": inbound_anchors,
        }
        built = chunk_body(page.body_text, page.title)
        synthetic = page_chunk(source)
        chunks = ([synthetic] if synthetic else []) + built
        for i, c in enumerate(chunks):
            c["ordinal"] = i
        await site_chunks.replace_for_page(
            db, page.user_id, page.site_id, page.id, page.content_hash, chunks
        )
        await site_pages.mark_chunked(db, page.id, page.content_hash if chunks else None)
        return len(chunks)

    async def _prune_unserved_chunks(self, db) -> None:
        unserved = await site_pages.unserved_page_ids(db)
        if await site_chunks.delete_by_page_ids(db, unserved) > 0:
            await site_pages.clear_chunked_hash(db, unserved)

    async def _mark_chunk_failed(self, db, chunk_id: str, message: str) -> None:
        trimmed = message[:MAX_ERROR_CHARS]
        failed = await site_chunks.mark_embed_failed(db, chunk_id, trimmed)
        if failed is not None and failed[1] >= MAX_EMBED_ATTEMPTS:
            await site_pages.mark_embed_failed(db, failed[0], trimmed)


embed_worker_service = EmbedWorkerService()
