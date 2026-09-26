import sys

from src.core.database import unit_of_work
from src.embed_worker.chunking import chunk_body, page_chunk
from src.embed_worker.embedding import passage_input, post_input, query_input
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageChunkSource
from src.social_listening.repositories.posts import social_listening_posts
from src.social_listening.repositories.queries import social_listening_queries

MAX_EMBED_ATTEMPTS = 3
MAX_ERROR_CHARS = 500


class EmbedWorkerService:
    async def run_chunk_pass(self, page_batch: int) -> tuple[int, int]:
        async with unit_of_work() as db:
            await self._prune_unserved_chunks(db)
            pages = await site_pages.list_needing_chunks(db, page_batch)
            anchors = await site_page_links.inbound_anchors_by_page_ids(db, [p.id for p in pages])
        chunks = 0
        for page in pages:
            try:
                chunks += await self._rechunk_page(page, anchors.get(page.id, []))
            except Exception as e:
                print(f"embed-worker: could not chunk {page.url} — {e}", file=sys.stderr)
        return len(pages), chunks

    async def run_embed_pass(
        self, embedder, model: str, batch: int = 32, max_batches: int = 4
    ) -> int:
        done = 0
        for _ in range(max_batches):
            async with unit_of_work() as db:
                rows = await site_chunks.list_pending_embeddings(db, MAX_EMBED_ATTEMPTS, batch)
                titles = {
                    p.id: p.title
                    for p in await site_pages.list_by_ids(db, None, [r.page_id for r in rows])
                }
            if not rows:
                break

            inputs = [passage_input(titles.get(r.page_id), r.heading_path, r.text) for r in rows]
            try:
                vectors = embedder.embed(inputs)
            except Exception as e:
                for r in rows:
                    await self._mark_chunk_failed(r.id, str(e))
                break

            touched: set[str] = set()
            for row, vector in zip(rows, vectors):
                try:
                    async with unit_of_work() as db:
                        await site_chunks.write_embedding(db, row.id, row.from_hash, vector, model)
                    touched.add(row.page_id)
                    done += 1
                except Exception as e:
                    await self._mark_chunk_failed(row.id, str(e))
            try:
                async with unit_of_work() as db:
                    incomplete = await site_chunks.page_ids_with_unembedded(db, list(touched))
                    await site_pages.clear_embed_state(db, list(touched - incomplete))
            except Exception:
                pass
        return done

    async def run_listening_pass(
        self, embedder, model: str, batch: int = 4, max_batches: int = 16
    ) -> int:
        done = 0
        for repository, to_input in (
            (social_listening_queries, lambda r: query_input(r.text)),
            (social_listening_posts, lambda r: post_input(r.title, r.text)),
        ):
            for _ in range(max_batches):
                async with unit_of_work() as db:
                    rows = await repository.list_pending_embeddings(db, MAX_EMBED_ATTEMPTS, batch)
                if not rows:
                    break
                try:
                    vectors = embedder.embed([to_input(r) for r in rows])
                except Exception as e:
                    for r in rows:
                        await self._mark_listening_failed(repository, r.id, str(e))
                    break
                for row, vector in zip(rows, vectors):
                    try:
                        async with unit_of_work() as db:
                            await repository.write_embedding(db, row.id, vector, model)
                        done += 1
                    except Exception as e:
                        await self._mark_listening_failed(repository, row.id, str(e))
        return done

    async def _rechunk_page(self, page: SitePageChunkSource, inbound_anchors: list[str]) -> int:
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
        async with unit_of_work() as db:
            await site_chunks.replace_for_page(
                db, page.user_id, page.site_id, page.id, page.content_hash, chunks
            )
            await site_pages.mark_chunked(db, page.id, page.content_hash if chunks else None)
        return len(chunks)

    async def _prune_unserved_chunks(self, db) -> None:
        unserved = await site_pages.unserved_page_ids(db)
        if await site_chunks.delete_by_page_ids(db, unserved) > 0:
            await site_pages.clear_chunked_hash(db, unserved)

    async def _mark_chunk_failed(self, chunk_id: str, message: str) -> None:
        trimmed = message[:MAX_ERROR_CHARS]
        async with unit_of_work() as db:
            failed = await site_chunks.mark_embed_failed(db, chunk_id, trimmed)
            if failed is not None and failed[1] >= MAX_EMBED_ATTEMPTS:
                await site_pages.mark_embed_failed(db, failed[0], trimmed)

    async def _mark_listening_failed(self, repository, row_id: str, message: str) -> None:
        async with unit_of_work() as db:
            await repository.mark_embed_failed(db, row_id, message)


embed_worker_service = EmbedWorkerService()
