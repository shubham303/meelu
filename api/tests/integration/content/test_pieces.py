from tests.integration.content.conftest import make_piece


async def test_pieces_crud(client, workspace):
    r = await client.post("/api/v1/content/pieces", json={})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "title is required."
    r = await client.post("/api/v1/content/pieces", json={"title": "X", "slug": "Not A Path!"})
    assert r.status_code == 400

    piece = await make_piece(
        client,
        title="Nashik pay",
        h1="  What Nashik  pays ",
        slug="Blog/nashik-pay/",
        targetKeyword=" Nashik  Pay ",
        bodyMarkdown="one two three",
    )
    assert piece["h1"] == "What Nashik pays"
    assert piece["slug"] == "/blog/nashik-pay"
    assert piece["targetKeyword"] == "nashik pay"
    assert piece["wordCount"] == 3
    assert piece["bodyMarkdown"] == "one two three"
    assert piece["createdBy"] == "user"
    assert "status" not in piece and "channelKey" not in piece
    assert "userId" not in piece and "seq" not in piece

    r = await client.get(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "Nashik pay"

    r = await client.patch(
        f"/api/v1/content/pieces/{piece['id']}",
        json={"bodyMarkdown": "a b", "metaDescription": "What the plant pays.", "slug": None},
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["wordCount"] == 2
    assert updated["metaDescription"] == "What the plant pays."
    assert updated.get("slug") is None

    r = await client.get(f"/api/v1/content/pieces/{piece['id']}/markdown")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/markdown")
    assert r.text == (
        '---\ntitle: "Nashik pay"\ndescription: "What the plant pays."\n'
        'keyword: "nashik pay"\n---\n\n# What Nashik pays\n\na b\n'
    )

    r = await client.delete(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/content/pieces/{piece['id']}")
    assert r.status_code == 404


async def test_pieces_list(client, workspace):
    a = await make_piece(client, title="Alpha grinder", bodyMarkdown="about beans")
    await make_piece(client, title="Beta", targetKeyword="burr grinder")
    r = await client.get("/api/v1/content/pieces")
    rows = r.json()["data"]
    assert r.json()["pagination"]["total"] == 2
    assert [p["title"] for p in rows] == ["Beta", "Alpha grinder"]
    assert "bodyMarkdown" not in rows[0]
    assert rows[0]["targetKeyword"] == "burr grinder"

    r = await client.get("/api/v1/content/pieces?search=beans")
    assert [p["id"] for p in r.json()["data"]] == [a["id"]]
    r = await client.get("/api/v1/content/pieces?search=burr")
    assert [p["title"] for p in r.json()["data"]] == ["Beta"]


async def test_page_checks(client, workspace):
    piece = await make_piece(client, title="T" * 61, bodyMarkdown="# Stray\n\nText.")
    assert {c["code"] for c in piece["checks"]} == {
        "title_length",
        "h1_missing",
        "meta_description_missing",
        "body_h1",
    }
    assert all(c["level"] == "warn" for c in piece["checks"])
    url = f"/api/v1/content/pieces/{piece['id']}"

    r = await client.patch(
        url,
        json={
            "title": "Espresso grind size",
            "h1": "How fine to grind for espresso",
            "metaDescription": "Short.",
            "targetKeyword": "espresso grind size",
            "bodyMarkdown": "## Start\n\nThe espresso grind size decides the shot.",
        },
    )
    checks = {c["code"]: c["message"] for c in r.json()["data"]["checks"]}
    assert set(checks) == {"meta_description_length", "keyword_placement"}
    assert checks["keyword_placement"].endswith("missing from the H1, meta description.")

    r = await client.patch(
        url,
        json={
            "h1": "Espresso grind size, dialled in",
            "metaDescription": "The espresso grind size that pulls a balanced shot, and how to "
            "move it when the shot runs fast or slow.",
        },
    )
    assert r.json()["data"]["checks"] == []


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
    assert second.get("anchorText") is None
    assert second.get("suggestion") is None
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


async def test_source_page_must_belong_to_the_site(client, workspace, email):
    from tests.integration.technical_seo.conftest import seed_pages, user_id_of

    user_id = await user_id_of(email)
    made = await seed_pages(workspace["id"], user_id, [{"url": "https://coffee.example.com/"}])
    page_id = next(iter(made.values()))

    r = await client.post("/api/v1/content/pieces", json={"title": "X", "sourcePageId": "pg_x"})
    assert r.status_code == 422
    piece = await make_piece(client, title="Y", sourcePageId=page_id)
    assert piece["sourcePageId"] == page_id
    r = await client.patch(
        f"/api/v1/content/pieces/{piece['id']}", json={"sourcePageId": "pg_elsewhere"}
    )
    assert r.status_code == 422
