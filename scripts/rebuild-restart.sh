#!/usr/bin/env bash
# Rebuild the docker images, restart the containers (api, agent server, worker,
# dashboard), wait for the agent server, then start the app.
#
# Usage:
#   scripts/rebuild-restart.sh            # docker compose up -d --build, then app dev
#   scripts/rebuild-restart.sh --no-cache # force a full rebuild, ignoring layer cache
#
# See DOCKER.md for what each docker compose command does and when to reach
# for --no-cache instead of the default cached rebuild.

set -euo pipefail

export BUILDX_NO_DEFAULT_ATTESTATIONS=1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ "${1:-}" == "--no-cache" ]]; then
  echo "==> Rebuilding all images (no cache)"
  docker compose build --no-cache
  echo "==> Restarting containers"
  docker compose up -d
else
  echo "==> Rebuilding changed images and restarting containers"
  docker compose up -d --build
fi

echo "==> Container status"
docker compose ps

AGENT_HEALTH="http://127.0.0.1:${AGENT_PORT:-8484}/health"
for _ in $(seq 1 60); do
  if curl -fsS --max-time 2 "$AGENT_HEALTH" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! curl -fsS --max-time 2 "$AGENT_HEALTH" >/dev/null 2>&1; then
  echo "!! Agent server did not come up on ${AGENT_HEALTH} — docker compose logs agent" >&2
  exit 1
fi
echo "==> Agent server up at ${AGENT_HEALTH}"

echo "==> Starting the app (cd app && npm run dev)"
cd "$ROOT_DIR/app"
npm run dev
