from tests.conftest import signup
from tests.integration.site_structure.helpers import BASE


async def test_jobs_crud(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "jobs.example.com", "name": "J"})
    assert r.status_code == 201, r.text

    r = await client.post(f"{BASE}/jobs", json={"prompt": "  Link the pricing page  "})
    assert r.status_code == 201, r.text
    job = r.json()["data"]
    assert job["prompt"] == "Link the pricing page"
    assert job["status"] == "RUNNING"
    assert "reconciled" not in job

    r = await client.post(f"{BASE}/jobs", json={"prompt": " "})
    assert r.status_code == 400

    r = await client.get(f"{BASE}/jobs")
    assert r.status_code == 200
    assert [j["id"] for j in r.json()["data"]] == [job["id"]]
    assert r.json()["pagination"]["total"] == 1

    r = await client.get(f"{BASE}/jobs/{job['id']}")
    assert r.json()["data"]["id"] == job["id"]
    r = await client.get(f"{BASE}/jobs/sjb_missing")
    assert r.status_code == 404

    r = await client.patch(f"{BASE}/jobs/{job['id']}", json={"status": "completed"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "COMPLETED"
    r = await client.patch(f"{BASE}/jobs/{job['id']}", json={"status": "sideways"})
    assert r.status_code == 400
    r = await client.patch(f"{BASE}/jobs/sjb_missing", json={"status": "FAILED"})
    assert r.status_code == 404


async def test_fail_stale_jobs_marks_old_running_jobs_failed(client, email):
    from datetime import UTC, datetime, timedelta

    from src.core.database import unit_of_work
    from src.site_structure.jobs.service import structure_job_service
    from src.site_structure.models.structure_job import StructureJob
    from tests.integration.site_structure.helpers import set_rows

    await signup(client, email)
    await client.post("/api/v1/sites", json={"domain": "stale.example.com", "name": "S"})
    old = (await client.post(f"{BASE}/jobs", json={"prompt": "Old"})).json()["data"]
    fresh = (await client.post(f"{BASE}/jobs", json={"prompt": "Fresh"})).json()["data"]
    await set_rows(StructureJob, [old["id"]], created_at=datetime.now(UTC) - timedelta(hours=2))

    async with unit_of_work() as db:
        assert await structure_job_service.fail_stale_jobs(db) >= 1

    assert (await client.get(f"{BASE}/jobs/{old['id']}")).json()["data"]["status"] == "FAILED"
    assert (await client.get(f"{BASE}/jobs/{fresh['id']}")).json()["data"]["status"] == "RUNNING"
