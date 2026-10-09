# Meelu desktop — the web UI in a window, the agent on your device

The app IS the web dashboard: the Electron window loads the same Next.js app
that serves the browser (`MEELU_BASE_URL`, normally `http://localhost:3000`).
One React codebase renders both surfaces, so the desktop app looks exactly
like the web UI because it *is* the web UI — no port, no divergence, nothing
to keep in sync.

What the app ADDS runs HERE, in the Electron main process, on the user's
device, with the user's own model (Anthropic by default, bring-your-own-key,
OpenRouter, or a local endpoint):

1. **The agent harness** (`src/main/agent/runner.js`, Claude Agent SDK). Each
   agentic action fetches its scope — write allowlist, system prompt, limits —
   from the dashboard at `GET /api/v1/agent/scope`, so web and app can never
   drift. The agent's data plane is the agent server (`../api/src/agent`, the
   `agent` compose service), reached over streamable HTTP at `MEELU_AGENT_MCP_URL` and authenticated with the
   signed-in account's workspace API key: direct SQL under RLS, the analytics
   algorithms, and a small set of controlled write tools. External MCP servers can
   attach per scope.
2. **Local workers** that call the dashboard REST API like any client: the
   crawler (`src/main/crawler/`), Search Console and Analytics syncs
   (`src/main/integrations/`), and the env-gated auto-crawl schedule.
3. **App-mode UI differences** — no marketing pages or docs chrome, plus the
   app-only Connections screen (model choice, Google OAuth, connectors).

Two channels, exactly as designed: normal UI operations call the dashboard
REST API directly from the page; everything device-side goes over one preload
bridge (`window.meelu`, `src/preload/index.cjs`) — agent turns and events,
crawls and syncs, connector management, analytics source files —
handled by IPC in `src/main/index.js`. The dashboard backend stays a dumb
CRUD API + database, which is what keeps hosting cheap and keeps every user's
LLM credential on their own machine.

## Run it

```bash
# 1. the api, agent server and dashboard (or ../scripts/rebuild-restart.sh does all of it)
docker compose up -d --build

# 2. the app — model choice in .env if you need one, see .env.example
cd app && npm install && npm run dev
```

Model choice lives in `app/.env`: nothing set uses your Claude Code login;
`ANTHROPIC_API_KEY` brings your own key; `OPENROUTER_API_KEY` +
`MEELU_OPENROUTER_MODEL` routes through OpenRouter (model ids are
provider-first, e.g. `anthropic/claude-sonnet-5`); `MEELU_LLM_BASE_URL` +
`MEELU_LLM_MODEL` points the harness at a local model (Ollama v0.12+ and
llama.cpp's `llama-server --jinja` both speak the Anthropic API natively,
at `:11434` and `:8080` respectively). The Connections screen sets the same
choices per device — including a dedicated llama.cpp provider that reads the
server's context size — and what it saves wins over `.env`.

Start order doesn't matter: if the dashboard server isn't up, the window
shows a waiting screen and connects by itself. Sign in happens in the window;
the session persists across app restarts. External links open in your
default browser.

## Verify

```bash
npm test                 # unit tests
npm run boot-test        # boots the window, exits on its own
npm run harness-smoke    # one read-only agent turn through the local harness
npm run agent-smoke      # MCP handshake against the agent server (needs MEELU_API_KEY)
MEELU_SHOT=/tmp/meelu.png npm run dev   # screenshot after load, then quits
```

## Deliberately later

Per-user onboarding (key entry UI instead of .env), keychain storage,
packaging/signing/auto-update.
