import re


def read_host(value: object) -> str | None:
    raw = str(value if value is not None else "").strip().lower()
    host = re.sub(r"^[a-z]+://", "", raw)
    host = re.sub(r"[/?#].*$", "", host)
    if not host or "." not in host or re.search(r"\s", host):
        return None
    return host
