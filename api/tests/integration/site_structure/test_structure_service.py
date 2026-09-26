import pytest
from fastapi import HTTPException

from tests.integration.site_structure.helpers import BASE, prepare_site, seed_link, set_page

ORIGIN = "https://top.example.com"


async def test_reconcile_covers_links_and_pillars_and_delete_routes_by_prefix(client, email):
    from src.core.database import unit_of_work
    from src.site_structure.service import site_structure_service

    site, user_id, pages, job = await prepare_site(
        client,
        email,
        "top.example.com",
        [{"url": f"{ORIGIN}/"}] + [{"url": f"{ORIGIN}/p{i}"} for i in range(4)],
    )
    p = [pages[f"{ORIGIN}/p{i}"] for i in range(4)]
    link = (
        await client.post(
            f"{BASE}/link-suggestions",
            json={"jobId": job["id"], "fromPageId": p[0], "toPageId": p[1], "suggestion": "s"},
        )
    ).json()["data"]
    other_link = (
        await client.post(
            f"{BASE}/link-suggestions",
            json={"jobId": job["id"], "fromPageId": p[1], "toPageId": p[2], "suggestion": "s"},
        )
    ).json()["data"]
    pillar_row = (
        await client.post(
            f"{BASE}/pillar-suggestions",
            json={"jobId": job["id"], "topic": "T", "memberPageIds": p[2:], "suggestion": "s"},
        )
    ).json()["data"]
    other_pillar = (
        await client.post(
            f"{BASE}/pillar-suggestions",
            json={"jobId": job["id"], "topic": "T", "memberPageIds": p[:2], "suggestion": "s"},
        )
    ).json()["data"]

    await seed_link(site["id"], user_id, p[0], p[1])
    await set_page(p[2], status=404)
    await set_page(p[3], status=404)
    async with unit_of_work() as db:
        result = await site_structure_service.reconcile(db, site["id"])
    assert result.model_dump() == {"links": {"removed": 2}, "pillars": {"removed": 1}}
    assert (await client.get(f"{BASE}/link-suggestions/{link['id']}")).status_code == 404
    assert (await client.get(f"{BASE}/link-suggestions/{other_link['id']}")).status_code == 404
    assert (await client.get(f"{BASE}/pillar-suggestions/{pillar_row['id']}")).status_code == 404

    async with unit_of_work() as db:
        gone = await site_structure_service.delete_suggestion(db, site["id"], other_pillar["id"])
    assert gone.model_dump(mode="json", by_alias=True) == {
        "id": other_pillar["id"],
        "kind": "pillar",
        "deleted": True,
    }
    assert (await client.get(f"{BASE}/pillar-suggestions/{other_pillar['id']}")).status_code == 404

    fresh = (
        await client.post(
            f"{BASE}/link-suggestions",
            json={"jobId": job["id"], "fromPageId": p[1], "toPageId": p[0], "suggestion": "s"},
        )
    ).json()["data"]
    async with unit_of_work() as db:
        gone = await site_structure_service.delete_suggestion(db, site["id"], fresh["id"])
    assert gone.kind == "link"
    assert (await client.get(f"{BASE}/link-suggestions/{fresh['id']}")).status_code == 404

    for missing in ("lks_missing0000", "plr_missing0000", "spg_whatever", "garbage"):
        async with unit_of_work() as db:
            with pytest.raises(HTTPException) as exc:
                await site_structure_service.delete_suggestion(db, site["id"], missing)
        assert exc.value.status_code == 404
