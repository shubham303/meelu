from pydantic import Field, computed_field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

LEDGER_KINDS = ("grant", "purchase", "usage", "refund", "adjustment")


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
