from dataclasses import dataclass

from pydantic import Field, computed_field

from src.core.schemas import EntityModel, JsDateTime, RequestModel


@dataclass(frozen=True)
class DueSite:
    site_id: str
    user_id: str
    status: str
    domain: str


def usd(micros: int) -> float:
    return round(micros / 1_000_000, 6)


class BalanceResponse(EntityModel):
    balance_micros: int
    balance_usd: float


class LedgerEntryResponse(EntityModel):
    id: str
    kind: str
    delta_micros: int
    balance_after_micros: int
    provider_call_id: str | None
    note: str | None
    created_at: JsDateTime

    @computed_field
    @property
    def delta_usd(self) -> float:
        return usd(self.delta_micros)

    @computed_field
    @property
    def balance_after_usd(self) -> float:
        return usd(self.balance_after_micros)


class GrantRequest(RequestModel):
    amount_usd: float = Field(gt=0)
    note: str | None = None


class SiteBillingResponse(EntityModel):
    site_id: str
    status: str
    last_charged_at: JsDateTime | None
    next_charge_at: JsDateTime | None
    charge_count: int
    charged_micros: int
    daily_price_micros: int


class SweepResult(EntityModel):
    considered: int = 0
    charged: int = 0
    disabled: int = 0
    reactivated: int = 0
    failed: int = 0
