from tests.integration.outreach.test_outreach import create_campaign, create_project


async def make_prospect(client, campaign_id, **overrides):
    body = {
        "name": "Ada",
        "email": "ada@bean.co",
        "campaignId": campaign_id,
        **overrides,
    }
    r = await client.post("/api/v1/outreach/prospects", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_conversation_lifecycle(client, site):
    project = await create_project(client)
    campaign = await create_campaign(client, project["id"])
    prospect = await make_prospect(client, campaign["id"])

    r = await client.post("/api/v1/outreach/conversations", json={"subject": "Hi"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): prospectId, body"}}

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={"prospectId": "pro_nope", "subject": "Hi", "body": "There"},
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "prospectId must reference an existing prospect."}}

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={
            "prospectId": prospect["id"],
            "subject": "Hi",
            "body": "There",
            "status": "queued",
        },
    )
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Invalid status. Allowed values: draft, sent, received."}
    }

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={
            "prospectId": prospect["id"],
            "subject": "Quick question",
            "body": "Hello",
            "from": "hello@beans.example",
            "cc": "team@beans.example",
        },
    )
    assert r.status_code == 201
    draft = r.json()["data"]
    assert draft["status"] == "draft"
    assert draft["from"] == "hello@beans.example"
    assert draft["cc"] == "team@beans.example"
    assert "bcc" not in draft
    assert draft["to"] == "ada@bean.co"
    assert draft["messageId"] is None
    assert draft["threadRef"] is None
    assert draft["siteId"] == site["id"]

    r = await client.get(f"/api/v1/outreach/prospects/{prospect['id']}")
    assert r.json()["data"]["status"] == "found"

    r = await client.put(
        f"/api/v1/outreach/conversations/{draft['id']}",
        json={"status": "sent", "prospectId": "pro_hijack", "messageId": "<abc@mail>"},
    )
    assert r.status_code == 200
    sent = r.json()["data"]
    assert sent["status"] == "sent"
    assert sent["prospectId"] == prospect["id"]
    assert sent["messageId"] == "abc@mail"

    r = await client.get(f"/api/v1/outreach/prospects/{prospect['id']}")
    assert r.json()["data"]["status"] == "contacted"

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={
            "prospectId": prospect["id"],
            "subject": "Re: Quick question",
            "body": "Sure, tell me more",
            "status": "received",
            "messageId": "<reply-1@mail>",
            "threadRef": "<abc@mail>",
            "occurredAt": "2026-01-02T03:04:05.000Z",
        },
    )
    assert r.status_code == 201
    reply = r.json()["data"]
    assert reply["status"] == "received"
    assert reply["threadRef"] == "abc@mail"
    assert reply["createdAt"] == "2026-01-02T03:04:05.000Z"

    r = await client.get(f"/api/v1/outreach/prospects/{prospect['id']}")
    assert r.json()["data"]["status"] == "replied"

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={
            "prospectId": prospect["id"],
            "subject": "Duplicate delivery",
            "body": "again",
            "status": "received",
            "messageId": "reply-1@mail",
        },
    )
    assert r.status_code == 201
    assert r.json()["data"]["id"] == reply["id"]
    assert r.json()["data"]["subject"] == "Re: Quick question"

    r = await client.get("/api/v1/outreach/conversations")
    listed = r.json()["data"]
    assert [m["id"] for m in listed] == [reply["id"], sent["id"]]

    r = await client.get("/api/v1/outreach/conversations", params={"status": "sent"})
    assert [m["id"] for m in r.json()["data"]] == [sent["id"]]

    r = await client.get("/api/v1/outreach/conversations", params={"prospectId": "pro_other"})
    assert r.json()["data"] == []

    r = await client.get(f"/api/v1/outreach/conversations/{reply['id']}")
    assert r.json()["data"]["id"] == reply["id"]

    r = await client.delete(f"/api/v1/outreach/conversations/{reply['id']}")
    assert r.json()["data"] == {"deleted": True}
    r = await client.get(f"/api/v1/outreach/conversations/{reply['id']}")
    assert r.status_code == 404


async def test_conversation_sync_batch(client, site):
    project = await create_project(client)
    campaign = await create_campaign(client, project["id"])
    prospect = await make_prospect(client, campaign["id"])

    r = await client.post(
        "/api/v1/outreach/conversations",
        json={
            "messages": [
                {
                    "prospectId": prospect["id"],
                    "messageId": "<m-1@mail>",
                    "subject": "  ",
                    "body": "",
                },
                {"prospectId": prospect["id"], "subject": "No id", "body": "skip me"},
                {
                    "prospectId": prospect["id"],
                    "messageId": "m-1@mail",
                    "subject": "Same id",
                    "body": "skip me too",
                },
            ]
        },
    )
    assert r.status_code == 201
    result = r.json()["data"]
    assert result["skipped"] == 2
    assert len(result["added"]) == 1
    assert result["added"][0]["subject"] == "(no subject)"
    assert result["added"][0]["body"] == "(empty message)"
    assert result["added"][0]["status"] == "received"

    r = await client.get(f"/api/v1/outreach/prospects/{prospect['id']}")
    assert r.json()["data"]["status"] == "replied"
