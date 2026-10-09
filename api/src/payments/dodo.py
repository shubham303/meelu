import base64
import hashlib
import hmac
import time
from typing import Any

import httpx

from src.payments.schemas import DodoCheckout
from src.settings import settings

SIGNATURE_TOLERANCE_SECONDS = 300


class DodoError(Exception):
    pass


class DodoSignatureError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.dodo_payments_api_key and settings.dodo_payments_credits_product_id)


async def create_checkout(
    amount_cents: int,
    email: str,
    name: str,
    metadata: dict[str, str],
) -> DodoCheckout:
    body: dict[str, Any] = {
        "product_cart": [
            {
                "product_id": settings.dodo_payments_credits_product_id,
                "quantity": 1,
                "amount": amount_cents,
            }
        ],
        "customer": {"email": email, "name": name or email},
        "billing_currency": "USD",
        "return_url": settings.dodo_payments_return_url,
        "metadata": metadata,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{settings.dodo_payments_base_url.rstrip('/')}/checkouts",
            json=body,
            headers={"Authorization": f"Bearer {settings.dodo_payments_api_key}"},
        )
    if response.status_code >= 400:
        raise DodoError(f"Dodo Payments rejected the checkout ({response.status_code}).")
    data = response.json()
    if not data.get("checkout_url"):
        raise DodoError("Dodo Payments returned no checkout URL.")
    return DodoCheckout(session_id=data["session_id"], checkout_url=data["checkout_url"])


def verify_webhook(raw_body: bytes, headers: dict[str, str]) -> None:
    secret = settings.dodo_payments_webhook_secret
    if not secret:
        raise DodoSignatureError("Dodo webhook secret is not configured.")

    webhook_id = headers.get("webhook-id")
    timestamp = headers.get("webhook-timestamp")
    signatures = headers.get("webhook-signature")
    if not webhook_id or not timestamp or not signatures:
        raise DodoSignatureError("Missing webhook signature headers.")

    try:
        sent_at = int(timestamp)
    except ValueError as e:
        raise DodoSignatureError("Invalid webhook timestamp.") from e
    if abs(time.time() - sent_at) > SIGNATURE_TOLERANCE_SECONDS:
        raise DodoSignatureError("Webhook timestamp is outside the allowed window.")

    key = base64.b64decode(secret.removeprefix("whsec_"))
    signed = f"{webhook_id}.{timestamp}.".encode() + raw_body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

    for entry in signatures.split():
        version, _, signature = entry.partition(",")
        if version == "v1" and hmac.compare_digest(signature, expected):
            return
    raise DodoSignatureError("Webhook signature does not match.")
