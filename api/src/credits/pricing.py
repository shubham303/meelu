from src.settings import settings

FIXED_PRICES_MICROS: dict[tuple[str, str], int] = {}


def minimum_balance_micros() -> int:
    return round(settings.credits_minimum_balance_usd * 1_000_000)


def site_day_price_micros() -> int:
    return round(settings.credits_site_daily_usd * 1_000_000)


def vendor_call_price(domain: str, capability: str, vendor_cost_micros: int) -> int:
    fixed = FIXED_PRICES_MICROS.get((domain, capability))
    return fixed if fixed is not None else max(vendor_cost_micros, 0)
