from pydantic import Field, computed_field

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.credits.schemas import usd


class CheckoutRequest(RequestModel):
    amount_usd: float = Field(gt=0)


class CheckoutResponse(EntityModel):
    payment_id: str
    checkout_url: str


class DodoCheckout(EntityModel):
    session_id: str
    checkout_url: str


class PaymentRecord(EntityModel):
    id: str
    user_id: str
    status: str
    credit_micros: int
    checkout_session_id: str | None
    checkout_url: str | None
    dodo_payment_id: str | None
    paid_amount: int | None
    paid_currency: str | None
    credited_at: JsDateTime | None
    created_at: JsDateTime


class PaymentResponse(EntityModel):
    id: str
    status: str
    credit_micros: int
    checkout_url: str | None
    paid_amount: int | None
    paid_currency: str | None
    credited_at: JsDateTime | None
    created_at: JsDateTime

    @computed_field
    @property
    def credit_usd(self) -> float:
        return usd(self.credit_micros)


class WebhookResponse(EntityModel):
    received: bool = True
