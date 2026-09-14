from datetime import UTC, datetime, timedelta

from tests.integration.site_jobs.conftest import add_page, backdate_heartbeat, site_owner


async def open_crawl(client, **body):
    return await client.post("/api/v1/site/crawl-jobs", json=body)


async def test_crawl_lifecycle(client, site):
    r = await open_crawl(client, trigger="user", freshDays=7)
    assert r.status_code == 202, r.text
    opened = r.json()["data"]
    assert opened["started"] is True
    assert opened["job"]["status"] == "queued"
    assert opened["job"]["trigger"] == "user"
    assert opened["job"]["siteId"] == site["id"]
    assert opened["job"]["cutoffDays"] == 7
    assert opened["job"]["sitemapUrls"] == []
    assert opened["job"]["discovered"] == 0
    assert opened["job"]["complete"] is False

    plan = opened["plan"]
    assert plan["target"] == {
        "siteId": site["id"],
        "domain": "jobs.example.com",
        "name": "Jobs",
    }
    assert plan["concurrency"] == 8
    assert plan["batchSize"] == 25
    assert plan["sitemapUrls"] == []
    assert plan["known"] == []
    assert plan["linkFrontier"] == []
    assert plan["freshBefore"].endswith("Z")

    job_id = opened["job"]["id"]

    r = await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")
    assert r.status_code == 200, r.text
    claimed = r.json()["data"]
    assert claimed["job"]["status"] == "running"
    assert claimed["job"]["startedAt"] is not None
    assert claimed["target"]["domain"] == "jobs.example.com"
    assert claimed["known"] == []
    assert claimed["linkFrontier"] == []
    assert claimed["concurrency"] == 8
    assert claimed["batchSize"] == 25

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={"heartbeat": True, "fetched": 3, "queued": 5, "skipped": 1, "discovered": 9},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"stop": False}

    r = await client.get(f"/api/v1/site/crawl-jobs/{job_id}")
    beaten = r.json()["data"]
    assert beaten["fetched"] == 3
    assert beaten["queued"] == 5
    assert beaten["skipped"] == 1
    assert beaten["discovered"] == 9
    assert beaten["heartbeatAt"] is not None

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={
            "status": "completed",
            "discovered": 12,
            "skipped": 2,
            "fetched": 10,
            "queued": 0,
            "newPages": 4,
            "changed": 3,
            "unchanged": 3,
            "failed": 0,
            "pagesStored": 10,
            "complete": True,
            "notes": ["all good"],
            "sitemapUrls": ["https://jobs.example.com/a"],
            "sitemapsUsed": ["https://jobs.example.com/sitemap.xml"],
            "sitemapAtRoot": True,
            "sitemapUrlCount": 1,
            "robotsTxt": "User-agent: *",
            "robotsStatus": 200,
            "robotsFetchedAt": "2026-01-01T00:00:00.000Z",
            "llmsTxt": None,
            "llmsStatus": 404,
            "llmsFetchedAt": "2026-01-01T00:00:00.000Z",
        },
    )
    assert r.status_code == 200, r.text
    settled = r.json()["data"]
    assert settled["status"] == "completed"
    assert settled["complete"] is True
    assert settled["discovered"] == 12
    assert settled["fetched"] == 10
    assert settled["newPages"] == 4
    assert settled["changed"] == 3
    assert settled["unchanged"] == 3
    assert settled["pagesStored"] == 10
    assert settled["notes"] == ["all good"]
    assert settled["finishedAt"] is not None

    r = await client.get("/api/v1/site")
    updated = r.json()["data"]
    assert updated["robotsTxt"] == "User-agent: *"
    assert updated["robotsStatus"] == 200
    assert updated["llmsStatus"] == 404
    assert updated["sitemapAtRoot"] is True
    assert updated["sitemapUrlCount"] == 1
    assert updated["sitemapUrls"] == ["https://jobs.example.com/sitemap.xml"]
    assert updated["lastCrawledAt"] is not None

    r = await client.get("/api/v1/site/crawl-jobs")
    listed = r.json()["data"]
    assert listed["total"] == 1
    assert listed["shown"] == 1
    assert listed["offset"] == 0
    assert listed["jobs"][0]["id"] == job_id
    status = listed["status"]
    assert status["siteId"] == site["id"]
    assert status["domain"] == "jobs.example.com"
    assert status["jobId"] == job_id
    assert status["state"] == "completed"
    assert status["active"] is False
    assert status["fetched"] == 10
    assert status["lastCrawlComplete"] is True
    assert status["pages"] == 0


async def test_open_while_running(client, site):
    r = await open_crawl(client, trigger="api")
    assert r.status_code == 202
    first = r.json()["data"]["job"]

    r = await open_crawl(client, trigger="api")
    assert r.status_code == 409, r.text
    clash = r.json()["data"]
    assert clash["started"] is False
    assert clash["plan"] is None
    assert clash["job"]["id"] == first["id"]
    assert clash["reason"] == "A crawl of jobs.example.com is already running."


async def test_stop_surfaces_through_heartbeat(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={"status": "cancelling", "reason": "enough for now"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "cancelling"
    assert r.json()["data"]["stopReason"] == "enough for now"

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}", json={"heartbeat": True, "fetched": 4}
    )
    assert r.json()["data"] == {"stop": True}

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={"status": "cancelled", "fetched": 4, "pagesStored": 4, "complete": False},
    )
    assert r.status_code == 200
    settled = r.json()["data"]
    assert settled["status"] == "cancelled"
    assert settled["finishedAt"] is not None
    assert settled["fetched"] == 4

    r = await open_crawl(client)
    assert r.json()["data"]["started"] is True


async def test_stop_on_queued_job_cancels_outright(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]

    r = await client.patch(f"/api/v1/site/crawl-jobs/{job_id}", json={"status": "cancelling"})
    assert r.json()["data"]["status"] == "cancelled"
    assert r.json()["data"]["finishedAt"] is not None

    r = await client.patch(f"/api/v1/site/crawl-jobs/{job_id}", json={"status": "cancelling"})
    assert r.status_code == 409
    assert "already finished (cancelled)" in r.json()["error"]["message"]


async def test_reap_stalled_job(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")

    r = await client.post("/api/v1/site/crawl-jobs/reap", json={})
    body = r.json()["data"]
    assert body["reaped"] == 0
    assert body["jobs"] == []
    assert body["note"].startswith("Nothing was stuck.")

    await backdate_heartbeat(job_id, 30)

    r = await client.post("/api/v1/site/crawl-jobs/reap", json={"staleMs": 60000})
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["reaped"] == 1
    assert body["jobs"][0]["id"] == job_id
    assert body["jobs"][0]["status"] == "failed"
    assert body["jobs"][0]["error"] == "no progress reported — the process running it is gone"
    assert body["note"].startswith("These crawls had stopped reporting")

    r = await open_crawl(client)
    assert r.status_code == 202


async def test_open_reaps_when_asked(client, site):
    r = await open_crawl(client)
    first = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{first}/claim")

    r = await open_crawl(client, reap=True, staleMs=1)
    assert r.status_code == 202, r.text
    body = r.json()["data"]
    assert body["started"] is True
    assert [j["id"] for j in body["reaped"]] == [first]
    assert body["reaped"][0]["error"] == "no progress reported — the process running it is gone"


async def test_freshness_cutoff(client, site):
    r = await open_crawl(client, freshDays=3)
    job = r.json()["data"]["job"]
    assert job["cutoffDays"] == 3
    fresh_before = datetime.fromisoformat(job["freshBefore"].replace("Z", "+00:00"))
    expected = datetime.now(UTC) - timedelta(days=3)
    assert abs((fresh_before - expected).total_seconds()) < 60
    await client.patch(f"/api/v1/site/crawl-jobs/{job['id']}", json={"status": "cancelling"})

    r = await open_crawl(client, freshDays=0)
    job = r.json()["data"]["job"]
    assert job["cutoffDays"] == 0
    assert "freshBefore" not in job
    assert r.json()["data"]["plan"]["freshBefore"] is None
    await client.patch(f"/api/v1/site/crawl-jobs/{job['id']}", json={"status": "cancelling"})

    r = await open_crawl(client)
    job = r.json()["data"]["job"]
    assert job["cutoffDays"] == 7
    await client.patch(f"/api/v1/site/crawl-jobs/{job['id']}", json={"status": "cancelling"})

    stamp = (datetime.now(UTC) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    r = await open_crawl(client, freshBefore=stamp)
    job = r.json()["data"]["job"]
    assert job["cutoffDays"] == 10
    assert job["freshBefore"].startswith(stamp[:10])
    await client.patch(f"/api/v1/site/crawl-jobs/{job['id']}", json={"status": "cancelling"})

    r = await open_crawl(client, freshBefore="not a date")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "freshBefore must be an ISO timestamp."}}


async def test_sitemap_urls_land_on_the_site_record(client, site):
    r = await open_crawl(client, sitemapUrls=["https://jobs.example.com/sitemap.xml", "  "])
    assert r.status_code == 202
    job = r.json()["data"]["job"]
    assert job["sitemapUrls"] == ["https://jobs.example.com/sitemap.xml"]
    assert r.json()["data"]["plan"]["sitemapUrls"] == ["https://jobs.example.com/sitemap.xml"]

    r = await client.get("/api/v1/site")
    assert r.json()["data"]["sitemapUrls"] == ["https://jobs.example.com/sitemap.xml"]


async def test_settle_warns_when_the_sitemap_drops(client, site):
    owner = await site_owner(site["id"])
    urls = [f"https://jobs.example.com/p{i}" for i in range(24)]
    for url in urls:
        await add_page(site["id"], owner, url, status=200)

    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={
            "status": "completed",
            "complete": True,
            "sitemapComplete": True,
            "sitemapUrls": urls[:5],
            "notes": ["crawl finished"],
        },
    )
    assert r.status_code == 200, r.text
    notes = r.json()["data"]["notes"]
    assert notes[0] == "crawl finished"
    assert notes[1] == (
        "The sitemap now lists 5 of the 24 pages known for this site — that is a large "
        "drop; check the sitemap before treating those pages as retired."
    )


async def test_settle_merges_crawler_access_and_host_variants(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={
            "status": "completed",
            "complete": True,
            "crawlerAccess": {
                "checkedAt": "2026-01-01T00:00:00.000Z",
                "url": "https://jobs.example.com/",
                "baseline": {"status": 200, "bytes": 1024},
                "agents": [{"agent": "GPTBot", "status": 403, "verdict": "blocked"}],
            },
            "hostVariants": {
                "checkedAt": "2026-01-01T00:00:00.000Z",
                "preferred": "https://jobs.example.com",
                "variants": [
                    {
                        "kind": "host",
                        "url": "https://www.jobs.example.com",
                        "verdict": "redirects",
                        "status": 301,
                    }
                ],
            },
        },
    )
    assert r.status_code == 200, r.text

    r = await client.get("/api/v1/site")
    saved = r.json()["data"]
    assert saved["crawlerAccess"]["baseline"] == {"status": 200, "bytes": 1024}
    assert saved["crawlerAccess"]["agents"][0]["agent"] == "GPTBot"
    assert saved["crawlerAccess"]["agents"][0]["verdict"] == "blocked"
    assert saved["hostVariants"]["preferred"] == "https://jobs.example.com"
    assert saved["hostVariants"]["variants"][0]["kind"] == "host"


async def test_settle_failed_records_the_error(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]
    await client.post(f"/api/v1/site/crawl-jobs/{job_id}/claim")

    r = await client.patch(
        f"/api/v1/site/crawl-jobs/{job_id}",
        json={"status": "failed", "error": "host unreachable", "pagesStored": 0},
    )
    assert r.status_code == 200, r.text
    settled = r.json()["data"]
    assert settled["status"] == "failed"
    assert settled["error"] == "host unreachable"
    assert settled["complete"] is False

    r = await client.get("/api/v1/site/crawl-jobs")
    assert r.json()["data"]["status"]["state"] == "failed"
    assert r.json()["data"]["status"]["error"] == "host unreachable"


async def test_unknown_status_and_missing_job(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]

    r = await client.patch(f"/api/v1/site/crawl-jobs/{job_id}", json={"status": "wat"})
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith('Unknown status "wat".')

    r = await client.get("/api/v1/site/crawl-jobs/scj_missing0")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No crawl scj_missing0 for this website."}}


async def test_delete_stops_then_deletes(client, site):
    r = await open_crawl(client)
    job_id = r.json()["data"]["job"]["id"]

    r = await client.delete(f"/api/v1/site/crawl-jobs/{job_id}")
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["stopped"] is True
    assert body["deleted"] is False
    assert body["job"]["status"] == "cancelled"

    r = await client.delete(f"/api/v1/site/crawl-jobs/{job_id}")
    assert r.json()["data"] == {"stopped": False, "deleted": True}

    r = await client.get(f"/api/v1/site/crawl-jobs/{job_id}")
    assert r.status_code == 404


async def test_list_filters(client, site):
    r = await open_crawl(client, trigger="schedule")
    job_id = r.json()["data"]["job"]["id"]
    await client.patch(f"/api/v1/site/crawl-jobs/{job_id}", json={"status": "cancelling"})

    r = await client.get("/api/v1/site/crawl-jobs", params={"trigger": "schedule"})
    assert r.json()["data"]["total"] == 1
    r = await client.get("/api/v1/site/crawl-jobs", params={"trigger": "user"})
    assert r.json()["data"]["total"] == 0
    r = await client.get("/api/v1/site/crawl-jobs", params={"status": "cancelled"})
    assert r.json()["data"]["total"] == 1
    r = await client.get("/api/v1/site/crawl-jobs", params={"active": "false"})
    assert r.json()["data"]["total"] == 1
    r = await client.get("/api/v1/site/crawl-jobs", params={"active": "true"})
    assert r.json()["data"]["total"] == 0
    r = await client.get("/api/v1/site/crawl-jobs", params={"sort": "bogus"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "sort must be one of created, started, finished, fetched."}
    }
