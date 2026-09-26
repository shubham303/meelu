from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.precompute.rollup import seo_rollup_service
from src.seo.precompute.schemas import RollupResult
from src.seo.state.repository import seo_site_states
from src.seo.state.schemas import SiteStateRecord


class SeoPrecomputeService:
    async def run_rollup(self, db: AsyncSession, user_id: str, site_id: str) -> RollupResult:
        await seo_site_states.ensure(db, user_id, site_id)
        result = await seo_rollup_service.run(db, user_id, site_id)
        await db.commit()
        return result

    async def request_precompute(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> SiteStateRecord:
        await seo_site_states.ensure(db, user_id, site_id)
        await seo_site_states.request_precompute(db, site_id)
        found = await seo_site_states.get(db, site_id)
        assert found is not None
        return found


seo_precompute_service = SeoPrecomputeService()
