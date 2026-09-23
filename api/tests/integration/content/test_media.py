PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def upload(client, data=PNG, name="beans.png", content_type="image/png", **fields):
    return await client.post(
        "/api/v1/content/media",
        files={"file": (name, data, content_type)},
        data=fields,
    )


async def test_media_round_trip(client, workspace):
    r = await upload(client, width="1200", height="800")
    assert r.status_code == 201, r.text
    media = r.json()["data"]
    assert media["contentType"] == "image/png"
    assert media["byteSize"] == len(PNG)
    assert media["width"] == 1200
    assert media["height"] == 800
    assert media["originalName"] == "beans.png"
    assert media["id"].startswith("pmd_")
    assert "data" not in media
    assert "userId" not in media

    r = await client.get(f"/api/v1/content/media/{media['id']}")
    assert r.status_code == 200
    assert r.content == PNG
    assert r.headers["content-type"] == "image/png"
    assert r.headers["content-length"] == str(len(PNG))
    assert r.headers["cache-control"] == "private, max-age=31536000, immutable"

    r = await client.get("/api/v1/content/media/pmd_missing00")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}


async def test_media_without_dimensions(client, workspace):
    r = await upload(client)
    assert r.status_code == 201
    media = r.json()["data"]
    assert "width" not in media
    assert "height" not in media


async def test_media_rejects_bad_uploads(client, workspace):
    r = await client.post("/api/v1/content/media", json={"file": "nope"})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "Send the image as multipart/form-data."

    r = await client.post(
        "/api/v1/content/media",
        data={"width": "10"},
        files={"notes": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "Missing the `file` field."

    r = await upload(client, data=b"%PDF-1.4", name="brief.pdf", content_type="application/pdf")
    assert r.status_code == 400
    assert r.json()["error"]["message"] == (
        "Images only — JPEG, PNG, WebP or GIF. That one is application/pdf."
    )

    r = await upload(client, data=b"")
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "That file is empty."

    r = await upload(client, data=b"x" * (5 * 1024 * 1024 + 1))
    assert r.status_code == 400
    assert r.json()["error"]["message"] == (
        "That image is 5.0MB. The limit is 5MB — these are stored in Postgres, not a bucket."
    )


async def test_piece_can_reference_an_upload(client, workspace):
    media = (await upload(client)).json()["data"]

    r = await client.post(
        "/api/v1/content/pieces",
        json={
            "channelKey": "instagram",
            "title": "Beans",
            "bodyMarkdown": "Fresh roast.",
            "mediaSource": "upload",
            "mediaUploadId": media["id"],
            "mediaAlt": "  A bag of beans  ",
        },
    )
    assert r.status_code == 201, r.text
    post = r.json()["data"]
    assert post["mediaSource"] == "upload"
    assert post["mediaUploadId"] == media["id"]
    assert post["mediaUrl"] == f"/api/v1/content/media/{media['id']}"
    assert post["mediaAlt"] == "A bag of beans"

    r = await client.patch(
        f"/api/v1/content/pieces/{post['id']}",
        json={"mediaSource": "none"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "blocked"
    assert any(
        "won't take a post without an image" in c["message"] for c in r.json()["data"]["checks"]
    )

    r = await client.patch(f"/api/v1/content/pieces/{post['id']}", json={"mediaSource": "none"})
    assert r.status_code == 200
    cleared = r.json()["data"]
    assert cleared["mediaSource"] == "none"
    assert cleared["mediaUrl"] is None
    assert cleared["mediaUploadId"] is None
    assert cleared["status"] == "blocked"
    assert [c["code"] for c in cleared["checks"]] == ["requires_media"]

    r = await client.post(
        "/api/v1/content/pieces",
        json={
            "channelKey": "instagram",
            "title": "Ghost",
            "bodyMarkdown": "Missing upload.",
            "mediaSource": "upload",
            "mediaUploadId": "pmd_nothing00",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == ("That upload doesn't exist. Upload the image first.")
