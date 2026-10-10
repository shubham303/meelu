import base64
import hashlib
import hmac
import json
import time
import uuid

import pytest

from src.payments import dodo
from src.payments.schemas import DodoCheckout
from src.settings import settings
from tests.conftest import signup

SECRET = "whsec_" + base64.b64encode(b"test-webhook-secret").decode()


@pytest.fixture
def dodo_config(monkeypatch):
    monkeypatch.setattr(settings, "dodo_payments_api_key", "test-key")
    monkeypatch.setattr(settings, "dodo_payments_credits_product_id", "pdt_credits")
    monkeypatch.setattr(settings, "dodo_payments_webhook_secret", SECRET)
    calls = []

    async def create_checkout(amount_cents, email, name, metadata):
        calls.append({"amount_cents": amount_cents, "email": email, "metadata": metadata})
        session_id = f"cks_{uuid.uuid4().hex[:12]}"
        return DodoCheckout(
            session_id=session_id, checkout_url=f"https://checkout.test/{session_id}"
        )

    monkeypatch.setattr(dodo, "create_checkout", create_checkout)
    return calls


def signed(event: dict, secret: str = SECRET) -> tuple[bytes, dict]:
    body = json.dumps(event).encode()
    webhook_id = "msg_1"
    timestamp = str(int(time.time()))
    key = base64.b64decode(secret.removeprefix("whsec_"))
    digest = hmac.new(key, f"{webhook_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return body, {
        "webhook-id": webhook_id,
        "webhook-timestamp": timestamp,
        "webhook-signature": f"v1,{base64.b64encode(digest).decode()}",
        "content-type": "application/json",
    }


def succeeded(payment_id: str) -> dict:
    return {
        "business_id": "bus_1",
        "type": "payment.succeeded",
        "timestamp": "2026-10-08T10:00:00Z",
        "data": {
            "payload_type": "Payment",
            "payment_id": f"pay_dodo_{uuid.uuid4().hex[:12]}",
            "total_amount": 2000,
            "currency": "USD",
            "metadata": {"meelu_payment_id": payment_id},
        },
    }


async def test_checkout_creates_pending_payment(client, email, dodo_config):
    await signup(client, email)
    r = await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert created["checkoutUrl"].startswith("https://checkout.test/cks_")
    assert dodo_config[0]["amount_cents"] == 2000
    assert dodo_config[0]["metadata"]["meelu_payment_id"] == created["paymentId"]

    r = await client.get(f"/api/v1/payments/{created['paymentId']}")
    payment = r.json()["data"]
    assert payment["status"] == "pending"
    assert payment["creditUsd"] == 20


async def test_checkout_rejects_out_of_range(client, email, dodo_config):
    await signup(client, email)
    r = await client.post("/api/v1/payments/checkout", json={"amountUsd": 1})
    assert r.status_code == 400


async def test_checkout_unconfigured(client, email, monkeypatch):
    monkeypatch.setattr(settings, "dodo_payments_api_key", "")
    await signup(client, email)
    r = await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})
    assert r.status_code == 503


async def test_webhook_credits_once(client, email, dodo_config):
    await signup(client, email)
    before = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]
    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]

    body, headers = signed(succeeded(payment_id))
    for _ in range(2):
        r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
        assert r.status_code == 200, r.text

    after = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]
    assert after - before == 20_000_000

    payment = (await client.get(f"/api/v1/payments/{payment_id}")).json()["data"]
    assert payment["status"] == "succeeded"
    assert payment["paidAmount"] == 2000
    assert payment["creditedAt"]

    ledger = (await client.get("/api/v1/credits/ledger")).json()["data"]
    assert [e["kind"] for e in ledger].count("purchase") == 1


async def test_webhook_rejects_bad_signature(client, email, dodo_config):
    await signup(client, email)
    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]
    wrong = "whsec_" + base64.b64encode(b"other").decode()
    body, headers = signed(succeeded(payment_id), secret=wrong)
    r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
    assert r.status_code == 401

    payment = (await client.get(f"/api/v1/payments/{payment_id}")).json()["data"]
    assert payment["status"] == "pending"


async def test_webhook_failed_payment(client, email, dodo_config):
    await signup(client, email)
    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]
    event = {**succeeded(payment_id), "type": "payment.failed"}
    body, headers = signed(event)
    r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
    assert r.status_code == 200
    payment = (await client.get(f"/api/v1/payments/{payment_id}")).json()["data"]
    assert payment["status"] == "failed"


async def test_payments_are_private(client, email, dodo_config):
    await signup(client, email)
    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]
    await signup(client, f"other-{email}")
    r = await client.get(f"/api/v1/payments/{payment_id}")
    assert r.status_code == 404


async def test_webhook_skips_wrong_currency_or_short_amount(client, email, dodo_config):
    await signup(client, email)
    before = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]

    for change in ({"currency": "EUR"}, {"total_amount": 1999}, {"total_amount": "2000"}):
        payment_id = (
            await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})
        ).json()["data"]["paymentId"]
        event = succeeded(payment_id)
        event["data"].update(change)
        body, headers = signed(event)
        r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
        assert r.status_code == 200, r.text
        payment = (await client.get(f"/api/v1/payments/{payment_id}")).json()["data"]
        assert payment["status"] == "pending"

    after = (await client.get("/api/v1/credits")).json()["data"]["balanceMicros"]
    assert after == before


async def test_webhook_is_exempt_from_the_origin_check(client, email, dodo_config):
    await signup(client, email)
    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]
    body, headers = signed(succeeded(payment_id))
    headers = {**headers, "origin": "https://dodo.example", "sec-fetch-site": "cross-site"}
    r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
    assert r.status_code == 200, r.text


async def test_paid_top_up_resumes_a_paused_site(client, email, dodo_config):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    from src.core.database import unit_of_work
    from src.credits.billing import site_billing_service

    await signup(client, email)
    site = (
        await client.post("/api/v1/sites", json={"domain": "paid.example", "name": "Paid"})
    ).json()["data"]
    async with unit_of_work() as db:
        await db.execute(
            text("UPDATE credit_account SET balance_micros = 0 WHERE user_id = :u"),
            {"u": (await client.get("/api/auth/me")).json()["data"]["id"]},
        )
        await db.execute(
            text("UPDATE site_billing SET last_charged_at = :t WHERE site_id = :s"),
            {"t": datetime.now(UTC) - timedelta(hours=25), "s": site["id"]},
        )
    await site_billing_service.sweep()
    assert (await client.get(f"/api/v1/sites/{site['id']}")).json()["data"]["status"] == "disabled"

    payment_id = (await client.post("/api/v1/payments/checkout", json={"amountUsd": 20})).json()[
        "data"
    ]["paymentId"]
    body, headers = signed(succeeded(payment_id))
    r = await client.post("/api/v1/payments/webhooks/dodo", content=body, headers=headers)
    assert r.status_code == 200, r.text

    state = (await client.get(f"/api/v1/sites/{site['id']}")).json()["data"]
    assert state["status"] == "active"
    assert state.get("pausedAt") is None
    r = await client.get("/api/v1/site/pages")
    assert r.status_code == 200, r.text
