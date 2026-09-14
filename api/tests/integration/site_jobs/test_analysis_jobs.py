from tests.integration.site_jobs.conftest import add_page, site_owner


async def test_analysis_lifecycle(client, site):
    owner = await site_owner(site["id"])
    page_id = await add_page(
        site["id"],
        owner,
        "https://jobs.example.com/one",
        status=200,
        body_text="a page about coffee grinders",
        content_hash="hash-one",
    )

    r = await client.get("/api/v1/site/analysis-jobs")
    idle = r.json()["data"]["status"]
    assert idle["state"] == "idle"
    assert idle["jobId"] is None
    assert idle["active"] is False
    assert idle["analyzedPages"] == 0
    assert idle["eligiblePages"] == 1

    r = await client.post("/api/v1/site/analysis-jobs", json={"trigger": "user"})
    assert r.status_code == 202, r.text
    opened = r.json()["data"]
    assert opened["started"] is True
    assert opened["job"]["status"] == "queued"
    assert opened["job"]["trigger"] == "user"
    assert opened["job"]["total"] == 0
    job_id = opened["job"]["id"]

    r = await client.post("/api/v1/site/analysis-jobs", json={})
    assert r.status_code == 409
    clash = r.json()["data"]
    assert clash["started"] is False
    assert clash["job"]["id"] == job_id
    assert clash["reason"] == "A page analysis of jobs.example.com is already running."

    r = await client.post(f"/api/v1/site/analysis-jobs/{job_id}/claim")
    assert r.status_code == 200, r.text
    plan = r.json()["data"]
    assert plan["job"]["status"] == "running"
    assert plan["job"]["total"] == 1
    assert plan["target"] == {"siteId": site["id"], "domain": "jobs.example.com"}
    assert plan["pages"] == [
        {
            "pageId": page_id,
            "url": "https://jobs.example.com/one",
            "contentHash": "hash-one",
            "analyzedFromHash": None,
        }
    ]

    r = await client.patch(
        f"/api/v1/site/analysis-jobs/{job_id}", json={"heartbeat": True, "processed": 1}
    )
    assert r.json()["data"] == {"stop": False}

    r = await client.patch(
        f"/api/v1/site/analysis-jobs/{job_id}",
        json={
            "status": "completed",
            "processed": 1,
            "skippedUnchanged": 0,
            "skippedSimilar": 0,
            "failed": 0,
        },
    )
    assert r.status_code == 200, r.text
    settled = r.json()["data"]
    assert settled["status"] == "completed"
    assert settled["processed"] == 1
    assert settled["total"] == 1
    assert settled["finishedAt"] is not None

    r = await client.get("/api/v1/site/analysis-jobs")
    status = r.json()["data"]["status"]
    assert status["state"] == "completed"
    assert status["jobId"] == job_id
    assert status["active"] is False
    assert status["processed"] == 1
    assert status["eligiblePages"] == 1


async def test_analysis_stop_surfaces_through_heartbeat(client, site):
    r = await client.post("/api/v1/site/analysis-jobs", json={})
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/analysis-jobs/{job_id}/claim")

    r = await client.patch(
        f"/api/v1/site/analysis-jobs/{job_id}",
        json={"status": "cancelling", "reason": "user changed their mind"},
    )
    assert r.json()["data"]["status"] == "cancelling"
    assert r.json()["data"]["stopReason"] == "user changed their mind"

    r = await client.patch(f"/api/v1/site/analysis-jobs/{job_id}", json={"heartbeat": True})
    assert r.json()["data"] == {"stop": True}

    r = await client.patch(
        f"/api/v1/site/analysis-jobs/{job_id}", json={"status": "cancelled", "processed": 2}
    )
    assert r.json()["data"]["status"] == "cancelled"
    assert r.json()["data"]["processed"] == 2


async def test_analysis_unknown_status_and_missing_job(client, site):
    r = await client.post("/api/v1/site/analysis-jobs", json={})
    job_id = r.json()["data"]["job"]["id"]

    r = await client.patch(f"/api/v1/site/analysis-jobs/{job_id}", json={"status": "wat"})
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith('Unknown status "wat".')

    r = await client.patch("/api/v1/site/analysis-jobs/saj_missing0", json={"heartbeat": True})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No page analysis saj_missing0 for this website."}}


async def test_page_analysis_save_and_read(client, site):
    owner = await site_owner(site["id"])
    page_id = await add_page(
        site["id"],
        owner,
        "https://jobs.example.com/two",
        status=200,
        body_text="grinders and burrs",
        content_hash="hash-two",
    )

    r = await client.get("/api/v1/site/page-analysis")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "pageId is required."}}

    r = await client.get("/api/v1/site/page-analysis", params={"pageId": page_id})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": f"Page {page_id} has not been analysed."}}

    r = await client.post(
        "/api/v1/site/page-analysis",
        json={
            "pageId": page_id,
            "topics": ["burrs", {"topic": " grinders ", "section": " Buying "}, {"topic": ""}],
            "keywords": ["burr grinder", "  ", "espresso"],
            "questionsAnswered": ["Which grinder?"],
            "analyzedFromHash": "hash-two",
            "analyzedText": "grinders and burrs",
            "model": "test-model",
        },
    )
    assert r.status_code == 201, r.text
    saved = r.json()["data"]
    assert saved["pageId"] == page_id
    assert saved["topics"] == [
        {"topic": "burrs", "section": None},
        {"topic": "grinders", "section": "Buying"},
    ]
    assert saved["keywords"] == ["burr grinder", "espresso"]
    assert saved["questionsAnswered"] == ["Which grinder?"]
    assert saved["analyzedFromHash"] == "hash-two"
    assert saved["model"] == "test-model"
    assert saved["analyzedAt"].endswith("Z")

    r = await client.get("/api/v1/site/page-analysis", params={"pageId": page_id})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == saved["id"]
    assert r.json()["data"]["analyzedText"] == "grinders and burrs"

    r = await client.post(
        "/api/v1/site/page-analysis",
        json={"pageId": page_id, "refreshOnly": True, "analyzedFromHash": "hash-three"},
    )
    assert r.status_code == 201
    assert r.json()["data"]["analyzedFromHash"] == "hash-three"
    assert r.json()["data"]["id"] == saved["id"]

    r = await client.post("/api/v1/site/page-analysis", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "pageId is required."}}

    r = await client.post("/api/v1/site/page-analysis", json={"pageId": "pg_missing00"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No page pg_missing00 for this website."}}


async def test_page_analysis_refresh_without_analysis(client, site):
    owner = await site_owner(site["id"])
    page_id = await add_page(
        site["id"], owner, "https://jobs.example.com/three", status=200, body_text="text"
    )

    r = await client.post(
        "/api/v1/site/page-analysis", json={"pageId": page_id, "refreshOnly": True}
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": f"Page {page_id} has no analysis to refresh."}}


async def test_analysis_candidates_reflect_prior_analysis(client, site):
    owner = await site_owner(site["id"])
    page_id = await add_page(
        site["id"],
        owner,
        "https://jobs.example.com/four",
        status=200,
        body_text="text",
        content_hash="hash-four",
    )
    await add_page(site["id"], owner, "https://jobs.example.com/empty", status=200, body_text="")
    await add_page(site["id"], owner, "https://jobs.example.com/gone", status=404)

    await client.post(
        "/api/v1/site/page-analysis",
        json={"pageId": page_id, "analyzedFromHash": "hash-four", "topics": ["x"]},
    )

    r = await client.post("/api/v1/site/analysis-jobs", json={})
    job_id = r.json()["data"]["job"]["id"]
    r = await client.post(f"/api/v1/site/analysis-jobs/{job_id}/claim")
    pages = r.json()["data"]["pages"]
    assert pages == [
        {
            "pageId": page_id,
            "url": "https://jobs.example.com/four",
            "contentHash": "hash-four",
            "analyzedFromHash": "hash-four",
        }
    ]
