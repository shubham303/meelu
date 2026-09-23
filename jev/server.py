import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from huggingface_hub import snapshot_download
from pydantic import BaseModel

MODEL_ID = os.environ.get("JEV_MODEL", "com-kotobalabs/open-jev-deberta-v3-large")
MAX_BODY_CHARS = 4000

model = None


def load():
    global model
    snapshot = snapshot_download(MODEL_ID)
    sys.path.insert(0, snapshot)
    from typed_decisions.open_jev import OpenJev

    model = OpenJev.from_pretrained(snapshot)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await asyncio.to_thread(load)
    yield


app = FastAPI(lifespan=lifespan)


class DecisionRequest(BaseModel):
    state: Any
    questions: dict[str, dict[str, Any]]
    model: str | None = None


def state_text(state: Any) -> str:
    if not isinstance(state, dict):
        return str(state)
    lines = []
    for key, value in state.items():
        if value in (None, ""):
            continue
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        if key == "body_text":
            text = text[:MAX_BODY_CHARS]
        lines.append(f"{key}: {text}")
    return "\n".join(lines)


def to_open_jev(q: dict[str, Any]) -> dict[str, Any]:
    kind = q["type"]
    instructions = q["instructions"]
    criteria = q.get("criteria")
    if kind == "choice":
        options = list(criteria)
        if isinstance(criteria, dict):
            legend = "\n".join(f"{o}: {criteria[o]}" for o in options if criteria[o])
            instructions = f"{instructions}\n{legend}" if legend else instructions
        return {"type": "choice", "instructions": instructions, "options": options}
    if kind == "noul":
        if isinstance(criteria, dict) and criteria.get("true"):
            instructions = f"{instructions} Yes means: {criteria['true']}"
        return {"type": "noul", "instructions": instructions}
    if kind == "score":
        return {"type": "score", "instructions": instructions, "options": [str(l) for l in criteria]}
    raise HTTPException(400, f"Unknown question type {kind!r}")


def to_answer(q: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    kind = q["type"]
    if kind == "noul":
        return {"type": "noul", "noul": out["noul"]}
    if kind == "choice":
        return {
            "type": "choice",
            "choice": out["choice"],
            "probabilities": out["probabilities"],
            "confidence": out["confidence"],
        }
    levels = list(out["probabilities"])
    return {
        "type": "score",
        "score": out["score"],
        "legend": {str(i): l for i, l in enumerate(levels)},
        "probabilities": {str(i): out["probabilities"][l] for i, l in enumerate(levels)},
        "confidence": out["confidence"],
    }


@app.get("/health")
def health():
    return {"ok": model is not None, "model": MODEL_ID}


@app.post("/decisions")
async def decisions(body: DecisionRequest):
    if model is None:
        raise HTTPException(503, "model still loading")
    keys = list(body.questions)
    questions = [to_open_jev(body.questions[k]) for k in keys]
    started = time.perf_counter()
    outputs = await asyncio.to_thread(model.decide, state_text(body.state), questions)
    answers = {k: to_answer(body.questions[k], o) for k, o in zip(keys, outputs)}
    return {
        "model": MODEL_ID,
        "answers": answers,
        "usage": {"cost": 0, "latency_ms": round((time.perf_counter() - started) * 1000)},
    }
