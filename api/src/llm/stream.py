import json
from dataclasses import dataclass
from typing import Any

DONE = "[DONE]"


@dataclass
class Usage:
    generation_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    cost_micros: int | None = None
    stopped: bool = False
    error: str | None = None

    def absorb(self, usage: Any) -> None:
        if not isinstance(usage, dict):
            return
        self.input_tokens = _count(usage.get("input_tokens"), self.input_tokens)
        self.output_tokens = _count(usage.get("output_tokens"), self.output_tokens)
        self.cache_read_tokens = _count(
            usage.get("cache_read_input_tokens"), self.cache_read_tokens
        )
        self.cache_write_tokens = _count(
            usage.get("cache_creation_input_tokens"), self.cache_write_tokens
        )
        cost = usage.get("cost")
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            self.cost_micros = round(cost * 1_000_000)

    def absorb_message(self, message: Any) -> None:
        if not isinstance(message, dict):
            return
        if isinstance(message.get("id"), str):
            self.generation_id = message["id"]
        self.absorb(message.get("usage"))


def _count(value: Any, current: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else current


class SseMeter:
    def __init__(self) -> None:
        self.usage = Usage()
        self._buffer = b""

    def feed(self, chunk: bytes) -> bytes:
        self._buffer += chunk.replace(b"\r\n", b"\n")
        out = []
        while b"\n\n" in self._buffer:
            frame, self._buffer = self._buffer.split(b"\n\n", 1)
            if self._read(frame):
                out.append(frame + b"\n\n")
        return b"".join(out)

    def flush(self) -> bytes:
        frame, self._buffer = self._buffer, b""
        return frame if frame.strip() and self._read(frame) else b""

    def _read(self, frame: bytes) -> bool:
        data = "\n".join(
            line[5:].lstrip()
            for line in frame.decode("utf-8", errors="replace").split("\n")
            if line.startswith("data:")
        )
        if not data:
            return True
        if data.strip() == DONE:
            return False
        try:
            event = json.loads(data)
        except ValueError:
            return True
        if not isinstance(event, dict):
            return True
        kind = event.get("type")
        if kind == "message_start":
            self.usage.absorb_message(event.get("message"))
        elif kind == "message_delta":
            self.usage.absorb(event.get("usage"))
        elif kind == "message_stop":
            self.usage.stopped = True
        elif kind == "error":
            error = event.get("error")
            self.usage.error = (
                str(error.get("message")) if isinstance(error, dict) else json.dumps(error)
            )
        return True
