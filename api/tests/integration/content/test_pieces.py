from tests.integration.content.conftest import make_piece


async def agent_headers(client, workspace):
    r = await client.post("/api/v1/keys", json={"name": "agent"})
    assert r.status_code == 201
    return {"x-api-key": r.json()["data"]["key"], "x-meelu-site": workspace["id"]}


async def test_pieces_crud(client, workspace):
    r = await client.post("/api/v1/content/pieces", json={"channelKey": "website"})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "title is required."
    r = await client.post("/api/v1/content/pieces", json={"title": "No channel"})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "channelKey is required."
    r = await client.post("/api/v1/content/pieces", json={"title": "X", "channelKey": "myspace"})
    assert r.status_code == 400

    piece = await make_piece(client, title="Nashik pay", bodyMarkdown="one two three")
    assert piece["status"] == "draft"
    assert piece["channelKey"] == "website"
    assert piece["wordCount"] == 3
    assert piece["bodyMarkdown"] == "one two three"
    assert piece["checks"] == []
    assert piece["scheduledAt"] is None
    assert piece["createdBy"] == "user"
    assert "userId" not in piece and "seq" not in piece

    r = await client.get(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "Nashik pay"

    r = await client.patch(
        f"/api/v1/content/pieces/{piece['id']}",
        json={"bodyMarkdown": "a b"},
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["wordCount"] == 2
    assert updated["status"] == "draft"

    r = await client.patch(f"/api/v1/content/pieces/{piece['id']}", json={"status": "ready"})
    assert r.status_code == 400

    r = await client.patch(f"/api/v1/content/pieces/{piece['id']}", json={"status": "published"})
    assert r.status_code == 400

    r = await client.get(f"/api/v1/content/pieces/{piece['id']}/markdown")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text == "---\ntitle: Nashik pay\n---\n\na b\n"

    r = await client.delete(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 404


async def test_pieces_list_and_counts(client, workspace):
    a = await make_piece(client, title="Alpha grinder", bodyMarkdown="about beans")
    b = await make_piece(
        client, title="Beta", channelKey="twitter", scheduledAt="2026-06-01T09:00:00Z"
    )
    r = await client.get("/api/v1/content/pieces")
    rows = r.json()["data"]
    assert r.json()["pagination"]["total"] == 2
    assert [p["title"] for p in rows] == ["Beta", "Alpha grinder"]
    assert "bodyMarkdown" not in rows[0]
    assert (rows[0]["channelKey"], rows[0]["status"], rows[0]["scheduledAt"]) == (
        "twitter",
        "draft",
        "2026-06-01T09:00:00.000Z",
    )

    r = await client.get("/api/v1/content/pieces?status=draft")
    assert [p["title"] for p in r.json()["data"]] == ["Beta", "Alpha grinder"]

    r = await client.get("/api/v1/content/pieces?channel=website")
    assert [p["title"] for p in r.json()["data"]] == ["Alpha grinder"]

    r = await client.get("/api/v1/content/pieces?search=beans")
    assert [p["id"] for p in r.json()["data"]] == [a["id"]]

    r = await client.get("/api/v1/content/pieces?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z")
    assert [p["title"] for p in r.json()["data"]] == ["Beta"]

    r = await client.get("/api/v1/content/pieces?status=bogus")
    assert r.status_code == 400
    r = await client.get("/api/v1/content/pieces?channel=myspace")
    assert r.status_code == 400

    r = await client.get("/api/v1/content/pieces?counts=true")
    assert r.json()["data"]["byStatus"] == {
        "draft": 2,
        "blocked": 0,
        "scheduled": 0,
        "posted": 0,
        "failed": 0,
    }


async def test_clone_piece(client, workspace):
    source = await make_piece(client, title="Origin", bodyMarkdown="one two", channelKey="linkedin")

    r = await client.post("/api/v1/content/pieces", json={"cloneFromPieceId": "cpc_nope"})
    assert r.status_code == 404

    r = await client.post("/api/v1/content/pieces", json={"cloneFromPieceId": source["id"]})
    assert r.status_code == 201, r.text
    clone = r.json()["data"]
    assert clone["title"] == "Origin (copy)"
    assert clone["bodyMarkdown"] == "one two"
    assert clone["channelKey"] == "linkedin"
    assert clone["parentPieceId"] == source["id"]
    assert clone["status"] == "draft"

    moved = await make_piece(
        client, cloneFromPieceId=source["id"], title="For X", channelKey="twitter"
    )
    assert moved["title"] == "For X"
    assert moved["channelKey"] == "twitter"
    assert moved["parentPieceId"] == source["id"]

    r = await client.delete(f"/api/v1/content/pieces/{source['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/content/pieces/{clone['id']}")
    assert r.json()["data"]["parentPieceId"] is None


async def test_hard_checks_block_and_unblock(client, workspace):
    piece = await make_piece(client, title="Long", channelKey="twitter", bodyMarkdown="x" * 300)
    assert piece["status"] == "blocked"
    assert [c["code"] for c in piece["checks"]] == ["character_limit"]
    assert "280" in piece["checks"][0]["message"]
    url = f"/api/v1/content/pieces/{piece['id']}"

    r = await client.patch(
        url,
        json={"bodyMarkdown": "Fits now. #one #two #three https://a.example https://b.example"},
    )
    fixed = r.json()["data"]
    assert fixed["status"] == "blocked"
    assert {c["code"]: c["level"] for c in fixed["checks"]} == {
        "max_links": "block",
        "max_hashtags": "warn",
    }

    r = await client.patch(url, json={"bodyMarkdown": "Fits now. #one https://a.example"})
    assert r.json()["data"]["status"] == "draft"
    assert r.json()["data"]["checks"] == []

    r = await client.patch(url, json={"bodyMarkdown": "x" * 281})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "blocked"

    r = await client.post(
        "/api/v1/content/pieces",
        json={
            "title": "Too long",
            "channelKey": "twitter",
            "bodyMarkdown": "x" * 300,
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["status"] == "blocked"


async def test_status_rules_for_agents_and_system(client, workspace):
    piece = await make_piece(client, title="Rules", channelKey="linkedin")
    url = f"/api/v1/content/pieces/{piece['id']}"
    AGENT = await agent_headers(client, workspace)

    r = await client.patch(url, json={"status": "posted"}, headers=AGENT)
    assert r.status_code == 400
    assert "Only a person" in r.json()["error"]["message"]

    r = await client.patch(url, json={"status": "scheduled"})
    assert r.status_code == 400

    r = await client.patch(url, json={"status": "draft"}, headers=AGENT)
    assert r.status_code == 200

    r = await client.patch(url, json={"status": "posted", "postedUrl": "https://li/1"})
    assert r.status_code == 200
    posted = r.json()["data"]
    assert posted["status"] == "posted"
    assert posted["postedUrl"] == "https://li/1"
    assert posted["postedAt"] is not None

    r = await client.patch(url, json={"bodyMarkdown": "rewrite"})
    assert r.status_code == 400
    r = await client.patch(url, json={"status": "draft"})
    assert r.status_code == 400


async def test_scheduling_respects_slots_gap_and_windows(client, workspace):
    await client.put(
        "/api/v1/content/channels/twitter",
        json={"minGapHours": 6, "timezone": "UTC"},
    )

    first = await make_piece(
        client, title="A", channelKey="twitter", scheduledAt="2026-06-01T09:20:00Z"
    )
    assert first["scheduledAt"] == "2026-06-01T09:00:00.000Z"

    r = await client.post(
        "/api/v1/content/pieces",
        json={"title": "B", "channelKey": "twitter", "scheduledAt": "2026-06-01T09:00:00Z"},
    )
    assert r.status_code == 409
    assert "already holds" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/content/pieces",
        json={"title": "B", "channelKey": "twitter", "scheduledAt": "2026-06-01T12:00:00Z"},
    )
    assert r.status_code == 409
    assert "Too close" in r.json()["error"]["message"]

    second = await make_piece(
        client, title="B", channelKey="twitter", scheduledAt="2026-06-01T16:00:00Z"
    )
    assert second["status"] == "draft"

    other = await make_piece(
        client, title="Elsewhere", channelKey="linkedin", scheduledAt="2026-06-01T09:00:00Z"
    )
    assert other["scheduledAt"] == "2026-06-01T09:00:00.000Z"

    r = await client.get(
        "/api/v1/content/channels/twitter/free-slots?from=2026-06-01T00:00:00Z&to=2026-06-02T00:00:00Z"
    )
    assert r.status_code == 200
    slots = r.json()["data"]
    assert slots["channelKey"] == "twitter"
    assert slots["minGapHours"] == 6
    assert "2026-06-01T09:00:00.000Z" not in slots["free"]
    assert "2026-06-01T12:00:00.000Z" not in slots["free"]
    assert "2026-06-01T16:00:00.000Z" not in slots["free"]
    assert [t["title"] for t in slots["taken"]] == ["A", "B"]

    r = await client.put(
        "/api/v1/content/channels/twitter",
        json={"postingWindows": [{"days": [0], "time": "18:00"}, {"days": [0], "time": "23:00"}]},
    )
    assert r.status_code == 200
    r = await client.get(
        "/api/v1/content/channels/twitter/free-slots?from=2026-06-01T00:00:00Z&to=2026-06-03T00:00:00Z"
    )
    assert r.json()["data"]["free"] == ["2026-06-01T23:00:00.000Z"]

    r = await client.get("/api/v1/content/channels/twitter/free-slots?from=x")
    assert r.status_code == 400
    r = await client.get(
        "/api/v1/content/channels/twitter/free-slots?from=2026-06-01T00:00:00Z&to=2026-09-01T00:00:00Z"
    )
    assert r.status_code == 400

    await client.put("/api/v1/content/channels/twitter", json={"enabled": False})
    r = await client.get("/api/v1/content/channels/twitter/free-slots")
    assert r.status_code == 400
    r = await client.post("/api/v1/content/pieces", json={"title": "Off", "channelKey": "twitter"})
    assert r.status_code == 400


async def test_piece_issues(client, workspace):
    piece = await make_piece(
        client, title="T", bodyMarkdown="The plant runs three shifts. Hires every quarter."
    )
    base = f"/api/v1/content/pieces/{piece['id']}/issues"

    r = await client.post(base, json={"tool": "readability", "issues": "no"})
    assert r.status_code == 400
    r = await client.post(base, json={"tool": "", "issues": []})
    assert r.status_code == 400

    r = await client.post(
        base,
        json={
            "tool": "readability",
            "issues": [
                {
                    "code": "long_sentence",
                    "title": "Sentence runs long",
                    "anchorText": "Hires every quarter.",
                    "suggestion": "It hires every quarter.",
                },
                {"code": "keyword_missing", "title": "No keyword", "anchorText": "not in body"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert created["tool"] == "readability"
    assert len(created["issues"]) == 2
    first, second = created["issues"]
    assert first["anchorText"] == "Hires every quarter."
    assert first["suggestion"] == "It hires every quarter."
    assert first["state"] == "open"
    assert second["anchorText"] is None
    assert second["suggestion"] is None
    assert first["runId"] == second["runId"] == created["runId"]

    r = await client.post(
        base, json={"tool": "seo", "issues": [{"code": "x", "title": "SEO thing"}]}
    )
    assert r.status_code == 201

    r = await client.get(base)
    assert len(r.json()["data"]) == 3
    r = await client.get(f"{base}?tool=seo")
    assert [i["title"] for i in r.json()["data"]] == ["SEO thing"]

    r = await client.patch(f"{base}/{first['id']}", json={"state": "nope"})
    assert r.status_code == 400
    r = await client.patch(f"{base}/{first['id']}", json={"state": "fixed"})
    assert r.json()["data"]["state"] == "fixed"
    r = await client.get(f"{base}?state=open")
    assert len(r.json()["data"]) == 2

    r = await client.post(base, json={"tool": "readability", "issues": []})
    assert r.status_code == 201
    r = await client.get(base)
    assert [i["tool"] for i in r.json()["data"]] == ["seo"]

    r = await client.get("/api/v1/content/pieces/cpc_missing/issues")
    assert r.status_code == 404


async def test_system_actor_sets_publishing_fields(client, workspace):
    piece = await make_piece(client, title="Facade", channelKey="linkedin")
    url = f"/api/v1/content/pieces/{piece['id']}"
    SYSTEM = {**(await agent_headers(client, workspace)), "x-meelu-actor": "system"}

    r = await client.patch(
        url, json={"status": "scheduled", "externalPostId": "pp_1"}, headers=SYSTEM
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "scheduled"
    assert r.json()["data"]["externalPostId"] == "pp_1"

    r = await client.patch(
        url,
        json={"status": "failed", "externalPostId": None, "failure": "bad aspect ratio"},
        headers=SYSTEM,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["failure"] == "bad aspect ratio"
    assert r.json()["data"]["externalPostId"] is None
