from tests.conftest import signup

GOAL = "Audit the site and hand the real issues to the user."
STEPS = "1. Crawl.\n2. Audit.\n3. Hand it over."


async def setup_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create_workflow(client, headers=None, **body):
    payload = {"goal": GOAL, "steps": STEPS, "desks": ["site", "pages"], **body}
    r = await client.post("/api/v1/workflows", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_workflows_crud(client, email):
    site = await setup_site(client, email)

    r = await client.post("/api/v1/workflows", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): goal, steps"}}

    r = await client.post("/api/v1/workflows", json={"goal": GOAL, "steps": STEPS})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "desks must be a non-empty list of desk ids."}}

    r = await client.post(
        "/api/v1/workflows", json={"goal": GOAL, "steps": STEPS, "desks": ["site", "legal"]}
    )
    assert r.status_code == 400
    assert r.json() == {
        "error": {
            "message": "Not a desk: legal. Allowed: site, pages, content, social, analytics."
        }
    }

    r = await client.post(
        "/api/v1/workflows", json={"goal": "g" * 301, "steps": STEPS, "desks": ["site"]}
    )
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Goal is too long — 300 characters at most. It is one sentence."}
    }

    r = await client.post(
        "/api/v1/workflows", json={"goal": GOAL, "steps": "s" * 4001, "desks": ["site"]}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Steps are too long — 4000 characters at most."}}

    workflow = await create_workflow(client, goal=f"  {GOAL}  ", desks=["site", "pages", "site"])
    assert workflow["goal"] == GOAL
    assert workflow["steps"] == STEPS
    assert workflow["desks"] == ["site", "pages"]
    assert workflow["seeded"] is False
    assert workflow["clonedFromId"] is None
    assert workflow["siteId"] == site["id"]
    assert "userId" not in workflow
    assert "seq" not in workflow

    second = await create_workflow(client, goal="Another workflow.")

    r = await client.get("/api/v1/workflows")
    assert r.status_code == 200
    authored = [w["id"] for w in r.json()["data"] if not w["seeded"]]
    assert authored == [second["id"], workflow["id"]]

    r = await client.get(f"/api/v1/workflows/{workflow['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == workflow["id"]

    r = await client.get("/api/v1/workflows/wfl_missing00")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.put(
        f"/api/v1/workflows/{workflow['id']}",
        json={"goal": "Edited goal.", "desks": ["content"]},
    )
    assert r.status_code == 200
    edited = r.json()["data"]
    assert edited["goal"] == "Edited goal."
    assert edited["desks"] == ["content"]
    assert edited["steps"] == STEPS

    r = await client.put(f"/api/v1/workflows/{workflow['id']}", json={"goal": "   "})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "goal cannot be empty."}}

    r = await client.put(f"/api/v1/workflows/{workflow['id']}", json={"steps": "  "})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "steps cannot be empty."}}

    r = await client.put(f"/api/v1/workflows/{workflow['id']}", json={"desks": []})
    assert r.status_code == 400

    r = await client.put("/api/v1/workflows/wfl_missing00", json={"goal": "x"})
    assert r.status_code == 404

    r = await client.put(f"/api/v1/workflows/{workflow['id']}", json={})
    assert r.status_code == 200

    r = await client.delete(f"/api/v1/workflows/{second['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"deleted": True}}

    r = await client.delete(f"/api/v1/workflows/{second['id']}")
    assert r.status_code == 404


async def test_workflow_clone(client, email):
    await setup_site(client, email)
    workflow = await create_workflow(client)

    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    assert r.status_code == 201
    other = r.json()["data"]
    here = {"x-meelu-site": workflow["siteId"]}

    r = await client.post(f"/api/v1/workflows/{workflow['id']}/clone", json={}, headers=here)
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "toSiteId is required — which website to clone onto."}}

    r = await client.post(
        f"/api/v1/workflows/{workflow['id']}/clone",
        json={"toSiteId": "site_nope0000"},
        headers=here,
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No website site_nope0000 in this workspace."}}

    r = await client.post(
        f"/api/v1/workflows/{workflow['id']}/clone",
        json={"toSiteId": workflow["siteId"]},
        headers=here,
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "That workflow is already on this site."}}

    r = await client.post(
        "/api/v1/workflows/wfl_missing00/clone", json={"toSiteId": other["id"]}, headers=here
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.post(
        f"/api/v1/workflows/{workflow['id']}/clone",
        json={"toSiteId": other["id"]},
        headers=here,
    )
    assert r.status_code == 201
    clone = r.json()["data"]
    assert clone["id"] != workflow["id"]
    assert clone["siteId"] == other["id"]
    assert clone["goal"] == workflow["goal"]
    assert clone["steps"] == workflow["steps"]
    assert clone["desks"] == workflow["desks"]
    assert clone["seeded"] is False
    assert clone["clonedFromId"] == workflow["id"]

    r = await client.get("/api/v1/workflows", headers={"x-meelu-site": other["id"]})
    assert [w["id"] for w in r.json()["data"] if not w["seeded"]] == [clone["id"]]


async def test_run_lifecycle(client, email):
    site = await setup_site(client, email)
    workflow = await create_workflow(client)

    r = await client.post("/api/v1/workflows/runs", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): workflowId"}}

    r = await client.post("/api/v1/workflows/runs", json={"workflowId": "wfl_missing00"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "That workflow does not exist on this site."}}

    r = await client.post("/api/v1/workflows/runs", json={"workflowId": workflow["id"]})
    assert r.status_code == 201
    run = r.json()["data"]
    assert run["workflowId"] == workflow["id"]
    assert run["siteId"] == site["id"]
    assert run["status"] == "running"
    assert run["stageIndex"] == 0
    assert run["stageDesk"] == "site"
    assert run["stageSummary"] is None
    assert run["error"] is None

    r = await client.get("/api/v1/workflows/runs")
    assert r.status_code == 200
    assert [x["id"] for x in r.json()["data"]] == [run["id"]]

    r = await client.get(f"/api/v1/workflows/runs/{run['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == run["id"]

    r = await client.get("/api/v1/workflows/runs/wfr_missing00")
    assert r.status_code == 404

    r = await client.patch(f"/api/v1/workflows/runs/{run['id']}", json={"status": "elsewhere"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {
            "message": "Invalid status. Allowed values: running, awaiting_review, done, stopped, failed."
        }
    }

    r = await client.patch(f"/api/v1/workflows/runs/{run['id']}", json={})
    assert r.status_code == 400

    r = await client.patch(
        f"/api/v1/workflows/runs/{run['id']}",
        json={
            "status": "awaiting_review",
            "stageIndex": 1,
            "stageDesk": "pages",
            "stageSummary": "Created 3 rows with pages.",
        },
    )
    assert r.status_code == 200
    parked = r.json()["data"]
    assert parked["status"] == "awaiting_review"
    assert parked["stageIndex"] == 1
    assert parked["stageDesk"] == "pages"
    assert parked["stageSummary"] == "Created 3 rows with pages."
    assert parked["error"] is None

    r = await client.patch("/api/v1/workflows/runs/wfr_missing00", json={"status": "done"})
    assert r.status_code == 404

    r = await client.post(f"/api/v1/workflows/runs/{run['id']}/continue")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "running"
    assert r.json()["data"]["stageIndex"] == 1

    r = await client.post(f"/api/v1/workflows/runs/{run['id']}/continue")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "This run is running, not awaiting review."}}

    r = await client.post("/api/v1/workflows/runs/wfr_missing00/continue")
    assert r.status_code == 404

    r = await client.post(f"/api/v1/workflows/runs/{run['id']}/stop")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "stopped"

    r = await client.post(f"/api/v1/workflows/runs/{run['id']}/continue")
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "This run is stopped, not awaiting review."}}

    r = await client.post("/api/v1/workflows/runs/wfr_missing00/stop")
    assert r.status_code == 404


async def test_run_failure_and_done_stages(client, email):
    await setup_site(client, email)
    workflow = await create_workflow(client, desks=["content", "analytics"])

    r = await client.post("/api/v1/workflows/runs", json={"workflowId": workflow["id"]})
    run = r.json()["data"]
    assert run["stageDesk"] == "content"

    r = await client.patch(
        f"/api/v1/workflows/runs/{run['id']}",
        json={"status": "failed", "error": "The orchestrator did not return a decision."},
    )
    assert r.status_code == 200
    failed = r.json()["data"]
    assert failed["status"] == "failed"
    assert failed["error"] == "The orchestrator did not return a decision."
    assert failed["stageDesk"] == "content"

    r = await client.patch(
        f"/api/v1/workflows/runs/{run['id']}",
        json={"status": "done", "stageSummary": "Every step is satisfied."},
    )
    assert r.status_code == 200
    done = r.json()["data"]
    assert done["status"] == "done"
    assert done["stageSummary"] == "Every step is satisfied."

    r = await client.patch(
        f"/api/v1/workflows/runs/{run['id']}",
        json={"status": "running", "stageDesk": None, "stageSummary": None, "error": None},
    )
    assert r.status_code == 200
    cleared = r.json()["data"]
    assert cleared["stageDesk"] is None
    assert cleared["stageSummary"] is None
    assert cleared["error"] is None

    r = await client.patch(
        f"/api/v1/workflows/runs/{run['id']}", json={"status": "running", "stageIndex": "2"}
    )
    assert r.status_code == 200
    assert r.json()["data"]["stageIndex"] == 2


async def test_runs_are_scoped_to_site(client, email):
    await setup_site(client, email)
    workflow = await create_workflow(client)
    here = {"x-meelu-site": workflow["siteId"]}

    r = await client.post("/api/v1/workflows/runs", json={"workflowId": workflow["id"]})
    run = r.json()["data"]

    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]
    there = {"x-meelu-site": other["id"]}

    r = await client.post(
        "/api/v1/workflows/runs", json={"workflowId": workflow["id"]}, headers=there
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "That workflow does not exist on this site."}}

    r = await client.get(f"/api/v1/workflows/runs/{run['id']}", headers=there)
    assert r.status_code == 404

    r = await client.get("/api/v1/workflows/runs", headers=there)
    assert r.json()["data"] == []

    r = await client.get("/api/v1/workflows/runs", headers=here)
    assert [x["id"] for x in r.json()["data"]] == [run["id"]]


async def test_seed_default_workflows(client, email):
    site = await setup_site(client, email)

    from sqlalchemy import select
    from src.workflows.defaults import DEFAULT_WORKFLOWS, seed_default_workflows

    from src.core.database import SessionLocal
    from src.profile.models.user import User

    async with SessionLocal() as db:
        user_id = (await db.execute(select(User.id).where(User.email == email))).scalar_one()
        await seed_default_workflows(db, user_id, site["id"])
        await db.commit()

    r = await client.get("/api/v1/workflows")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == len(DEFAULT_WORKFLOWS) == 3
    assert [w["goal"] for w in rows] == [w.goal for w in reversed(DEFAULT_WORKFLOWS)]
    for row in rows:
        assert row["seeded"] is True
        assert row["clonedFromId"] is None
        assert row["siteId"] == site["id"]
    assert [w["desks"] for w in rows] == [
        ["content", "analytics"],
        ["social"],
        ["site", "pages"],
    ]
    assert rows[-1]["steps"] == DEFAULT_WORKFLOWS[0].steps

    async with SessionLocal() as db:
        user_id = (await db.execute(select(User.id).where(User.email == email))).scalar_one()
        await seed_default_workflows(db, user_id, site["id"])
        await db.commit()

    r = await client.get("/api/v1/workflows")
    assert len(r.json()["data"]) == 3
