from typing import Any

from fastapi import Request

FORWARDED_KEYS = frozenset(
    {
        "messages",
        "system",
        "max_tokens",
        "metadata",
        "stop_sequences",
        "stream",
        "temperature",
        "top_k",
        "top_p",
        "tools",
        "tool_choice",
        "max_tool_calls",
        "thinking",
        "context_management",
        "output_config",
        "output_format",
    }
)


def forwarded(body: dict[str, Any], model_id: str, max_tokens: int) -> dict[str, Any]:
    sent = {k: v for k, v in body.items() if k in FORWARDED_KEYS}
    sent["model"] = model_id
    sent["max_tokens"] = max_tokens
    thinking = sent.get("thinking")
    if isinstance(thinking, dict) and isinstance(thinking.get("budget_tokens"), int):
        if thinking["budget_tokens"] >= max_tokens:
            sent["thinking"] = {**thinking, "budget_tokens": max(max_tokens // 2, 1)}
    return sent


async def read_limited(request: Request, limit: int) -> bytes | None:
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        return None
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def max_output_tokens(body: dict[str, Any]) -> int | None:
    value = body.get("max_tokens")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value
