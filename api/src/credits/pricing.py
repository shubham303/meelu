FIXED_PRICES_MICROS: dict[tuple[str, str], int] = {}

ACTION_PRICES_MICROS: dict[str, int] = {}


def vendor_call_price(domain: str, capability: str, vendor_cost_micros: int) -> int:
    fixed = FIXED_PRICES_MICROS.get((domain, capability))
    return fixed if fixed is not None else max(vendor_cost_micros, 0)


def action_price(action: str) -> int:
    return ACTION_PRICES_MICROS.get(action, 0)
