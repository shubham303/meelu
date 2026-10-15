import time

import httpx

from src.providers.http import _rate_limit_wait


def response(status, headers):
    return httpx.Response(status, headers=headers)


def test_retry_after_seconds():
    assert _rate_limit_wait(response(429, {"retry-after": "12"})) == 12


def test_github_reset_header():
    reset = str(int(time.time()) + 20)
    wait = _rate_limit_wait(
        response(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset})
    )
    assert 19 <= wait <= 22


def test_plain_forbidden_has_no_wait():
    assert _rate_limit_wait(response(403, {})) is None
    assert _rate_limit_wait(response(403, {"x-ratelimit-remaining": "12"})) is None
