FROM python:3.12-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
ENV UV_LINK_MODE=copy UV_HTTP_TIMEOUT=300

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project --extra agent

COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --extra agent

ENV PATH="/app/.venv/bin:$PATH"

FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS agent
EXPOSE 8484
CMD ["uvicorn", "src.agent.app:app", "--host", "0.0.0.0", "--port", "8484"]

FROM base AS migrator
CMD ["alembic", "upgrade", "head"]

FROM base AS embed-worker
ENV HF_HOME=/app/.cache/models
CMD ["python", "-m", "src.embed_worker"]
