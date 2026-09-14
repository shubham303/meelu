import secrets

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def uid(prefix: str) -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(10))
    return f"{prefix}_{body}"
