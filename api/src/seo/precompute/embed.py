from sqlalchemy.ext.asyncio import AsyncSession

from src.embed_worker.models import embed_model, embed_texts
from src.seo.precompute.coverage import seo_coverage_service
from src.seo.repositories import seo_keywords
from src.seo.schemas import KeywordVector

BATCH = 300


class SeoEmbedService:
    async def embed_pending(self, db: AsyncSession, user_id: str, site_id: str) -> int:
        done = 0
        while True:
            rows = await seo_keywords.pending_embedding(db, site_id, BATCH)
            if not rows:
                return done
            vectors = await embed_texts([f"query: {keyword}" for _, keyword in rows])
            if vectors is None:
                return done
            model = embed_model()
            embedded = [
                KeywordVector(id=row_id, keyword=keyword, embedding=[float(x) for x in vector])
                for (row_id, keyword), vector in zip(rows, vectors, strict=True)
            ]
            await seo_keywords.set_embeddings(
                db,
                [{"id": k.id, "embedding": str(k.embedding), "model": model} for k in embedded],
            )
            await seo_coverage_service.refresh(db, user_id, site_id, embedded, attach=True)
            done += len(embedded)


seo_embed_service = SeoEmbedService()
