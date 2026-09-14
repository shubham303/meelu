from __future__ import annotations

import pickle
import re
from pathlib import Path

from src.agent.context import AgentContext
from src.settings import settings


def _safe(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    if not cleaned:
        raise ValueError(f"Unusable model name {name!r}.")
    return cleaned


def _dir(ctx: AgentContext) -> Path:
    path = settings.agent_data_dir / "models" / ctx.schema
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_model(ctx: AgentContext, name: str, model) -> None:
    with open(_dir(ctx) / f"{_safe(name)}.pkl", "wb") as fh:
        pickle.dump(model, fh)


def load_model(ctx: AgentContext, name: str):
    path = _dir(ctx) / f"{_safe(name)}.pkl"
    if not path.exists():
        raise KeyError(f"No model {name!r}. Known: {list_models(ctx)}")
    with open(path, "rb") as fh:
        return pickle.load(fh)


def list_models(ctx: AgentContext) -> list[str]:
    return sorted(p.stem for p in _dir(ctx).glob("*.pkl"))
