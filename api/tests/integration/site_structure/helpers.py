from datetime import UTC, datetime

from sqlalchemy import text

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, user_id_of

BASE = "/api/v1/site/structure"

DIMS = 384


def vector(axis: int, wobble: float = 0.0) -> list[float]:
    v = [0.0] * DIMS
    v[axis] = 1.0
    v[(axis + 1) % DIMS] = wobble
    return v


async def seed_chunk(
    site_id, user_id, page_id, ordinal=1, heading=None, text_=None, embedding=None
):
    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_chunk import SiteChunk

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        row = SiteChunk(
            id=uid("chn"),
            user_id=user_id,
            site_id=site_id,
            page_id=page_id,
            ordinal=ordinal,
            heading_path=heading,
            text=text_ or f"Chunk {ordinal} of {page_id}",
            embedding=embedding,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        return row.id


async def seed_embedded_chunk(site_id, user_id, page_id, embedding, text_="A passage") -> str:
    return await seed_chunk(site_id, user_id, page_id, 1, None, text_, embedding)


async def seed_link(site_id, user_id, src, dst, region="body", anchor=None) -> None:
    from sqlalchemy import select

    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage
    from src.site_pages.models.site_page_link import SitePageLink

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        dst_url = (await db.execute(select(SitePage.url).where(SitePage.id == dst))).scalar_one()
        db.add(
            SitePageLink(
                id=uid("lnk"),
                user_id=user_id,
                site_id=site_id,
                src_page_id=src,
                dst_page_id=dst,
                dst_url=dst_url,
                external=False,
                region=region,
                anchor=anchor,
                created_at=now,
                updated_at=now,
            )
        )
        await db.commit()


async def drop_links(src, dst) -> None:
    from sqlalchemy import delete

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page_link import SitePageLink

    async with SessionLocal() as db:
        await db.execute(
            delete(SitePageLink).where(
                SitePageLink.src_page_id == src, SitePageLink.dst_page_id == dst
            )
        )
        await db.commit()


async def set_page(page_id, **values) -> None:
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage

    async with SessionLocal() as db:
        await db.execute(update(SitePage).where(SitePage.id == page_id).values(**values))
        await db.commit()


async def set_rows(model, ids, **values) -> None:
    from sqlalchemy import update

    from src.core.database import SessionLocal

    async with SessionLocal() as db:
        await db.execute(update(model).where(model.id.in_(list(ids))).values(**values))
        await db.commit()


async def workspace_table(user_id: str, name: str, columns: str, rows: list[tuple]) -> None:
    from src.agent.context import tenant_names
    from src.core.database import SessionLocal

    _, schema = tenant_names(user_id)
    async with SessionLocal() as db:
        await db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await db.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{name}"'))
        await db.execute(text(f'CREATE TABLE "{schema}"."{name}" ({columns})'))
        width = len(rows[0]) if rows else 0
        marks = ", ".join(f":c{i}" for i in range(width))
        for row in rows:
            await db.execute(
                text(f'INSERT INTO "{schema}"."{name}" VALUES ({marks})'),
                {f"c{i}": v for i, v in enumerate(row)},
            )
        await db.commit()


async def prepare_site(client, email, domain, pages):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": "Site"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    made = await seed_pages(site["id"], user_id, pages)
    r = await client.post(f"{BASE}/jobs", json={"prompt": "Structure run"})
    assert r.status_code == 201, r.text
    return site, user_id, made, r.json()["data"]


def fake_screener(monkeypatch, yes: float):
    from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter
    from src.providers.json_data_extractor.service import json_data_extractor
    from src.providers.registry import VendorResponse

    class Screener(JsonDataExtractorAdapter):
        id = "fake-screener"
        name = "Fake screener"
        capabilities = frozenset({DECIDE})
        charges = False

        async def decide(self, state, questions):
            return VendorResponse(
                {
                    "model": "fake",
                    "answers": {
                        key: {
                            "type": "choice",
                            "choice": "yes" if yes >= 0.5 else "no",
                            "probabilities": {"yes": yes, "no": 1.0 - yes},
                            "confidence": max(yes, 1.0 - yes),
                        }
                        for key in questions
                    },
                }
            )

    fake = Screener()
    monkeypatch.setattr(json_data_extractor, "adapters", [fake])
    return fake
