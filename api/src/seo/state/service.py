from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.keywords.repository import seo_keywords
from src.seo.state.repository import seo_site_states
from src.seo.state.schemas import SiteStateRecord, SiteStateUpdateRequest


class SeoStateService:
    async def get(self, db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
        return await seo_site_states.ensure(db, user_id, site_id)

    async def patch(
        self, db: AsyncSession, user_id: str, site_id: str, body: SiteStateUpdateRequest
    ) -> SiteStateRecord:
        await seo_site_states.ensure(db, user_id, site_id)
        patch = body.model_dump(exclude_none=True)
        if not patch:
            return await seo_site_states.ensure(db, user_id, site_id)
        updated = await seo_site_states.patch(db, site_id, patch)
        if "brand_terms" in patch:
            await seo_keywords.mark_branded(db, site_id, patch["brand_terms"])
        return updated

    def precompute_pending(self, state: SiteStateRecord) -> bool:
        return state.embedded_at is None or (
            state.precompute_requested_at is not None
            and state.precompute_requested_at > state.embedded_at
        )


seo_state_service = SeoStateService()
