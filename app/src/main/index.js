import { app, BrowserWindow, clipboard, ipcMain, Notification, shell } from "electron";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ENV_DEFAULTS, REPO_ROOT } from "./config.js";
import { connectSearchConsole } from "./integrations/gsc/oauth.js";
import { connectAnalytics } from "./integrations/ga/oauth.js";
import {
  checkSession,
  deleteSource,
  exportSource,
  exportText,
  readSource,
  resolvePaths,
  revealSource,
  saveSource,
} from "./analytics-store.js";
import { closeAgentSessions, runAgentTurn } from "./agent/runner.js";
import { requestCrawlStop, runCrawl } from "./crawler/index.js";
import { startSignalsSearch, stopSignalsSearch } from "./social-signals/pipeline.js";
import { startListeningSchedule } from "./social-signals/schedule.js";
import { startLeadsRun, stopLeadsRun } from "./leads/pipeline.js";
import { startLeadsSchedule } from "./leads/schedule.js";
import { requestRenderStop, runRender } from "./render/index.js";
import { AVAILABLE_CHECKS, runTextChecks } from "./text-checks/index.js";
import { inspectPageUrl, listGscProperties, requestSearchSyncStop, runIndexCheck, runSearchSync } from "./integrations/gsc/sync.js";
import { listGaProperties, requestTrafficSyncStop, runTrafficSync } from "./integrations/ga/sync.js";
import { startCrawlSchedule } from "./crawler/schedule.js";
import { createProviders } from "./providers/index.js";
import { clearOrphanedJobs } from "./orphaned-jobs.js";
import { appDir, screenshotDir } from "./paths.js";
import { crawlToken } from "./crawler/token.js";
import { describeLlmConfig, loadLlmConfig, saveLlmConfig } from "./integrations/llm/config.js";
import {
  connectorValues,
  listConnectors,
  removeConnector,
  saveConnector,
} from "./connector-config.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const BASE_URL = ENV_DEFAULTS.meeluBaseUrl;
const DASH_URL = `${BASE_URL}/dashboard`;

let win = null;
let connecting = false;

const permissionGrants = { full: false, always: new Set() };
const pendingPermissions = new Map();


const sessionUsage = {
  tokens: 0,
  inputTokens: 0,
  outputTokens: 0,
  costUsd: 0,
  turns: 0,
  startedAt: Date.now(),
};

function recordUsage(done) {
  const tokens = Number(done?.tokens);
  const inputTokens = Number(done?.inputTokens);
  const outputTokens = Number(done?.outputTokens);
  const cost = Number(done?.costUsd);
  sessionUsage.turns += 1;
  if (Number.isFinite(tokens) && tokens > 0) sessionUsage.tokens += tokens;
  if (Number.isFinite(inputTokens) && inputTokens > 0) sessionUsage.inputTokens += inputTokens;
  if (Number.isFinite(outputTokens) && outputTokens > 0) sessionUsage.outputTokens += outputTokens;
  if (Number.isFinite(cost) && cost > 0) sessionUsage.costUsd += cost;
}

function errorUsage(err) {
  return {
    tokens: Number(err?.tokens) || 0,
    inputTokens: Number(err?.inputTokens) || 0,
    outputTokens: Number(err?.outputTokens) || 0,
  };
}

const log = (...args) => console.log("[meelu]", ...args);

async function serverUp() {
  try {
    await fetch(BASE_URL, { signal: AbortSignal.timeout(2500) });
    return true;
  } catch {
    return false;
  }
}

async function connect() {
  if (connecting) return;
  connecting = true;
  try {
    if (!(await serverUp())) {
      await win.loadFile(path.join(here, "../renderer/waiting.html"));
      log(`waiting for the dashboard server at ${BASE_URL} …`);
      while (!(await serverUp())) {
        if (win.isDestroyed()) return;
        await new Promise((r) => setTimeout(r, 900));
      }
    }
    log(`dashboard server is up — loading ${DASH_URL}`);
    await win.loadURL(DASH_URL);
  } catch (err) {
    log("connect failed:", err.message);
  } finally {
    connecting = false;
  }
}

function agentCwd() {
  return appDir("agent-workspace");
}

function allowedSender(ev) {
  const url = ev.senderFrame?.url ?? "";
  return url === BASE_URL || url.startsWith(`${BASE_URL}/`);
}

function emitCrawl(event, data) {
  if (win && !win.isDestroyed()) win.webContents.send("crawl:event", { event, data });
}


function emitSignals(message) {
  if (win && !win.isDestroyed()) win.webContents.send("social-signals:event", message);
}

function emitLeads(message) {
  if (win && !win.isDestroyed()) win.webContents.send("leads:event", message);
}

function emitRender(event, data) {
  if (win && !win.isDestroyed()) win.webContents.send("render:event", { event, data });
}

async function sessionCookieHeader() {
  const cookies = await win.webContents.session.cookies.get({ url: BASE_URL });
  return cookies.map((c) => `${c.name}=${c.value}`).join("; ");
}

function connectorsFor() {
  return { get: (provider) => connectorValues(provider) };
}

function registerAgentIpc() {
  const turns = new Map();

  const startDriver = async (drive, onError) => {
    const turnId = crypto.randomUUID();
    const abortController = new AbortController();
    turns.set(turnId, abortController);
    const cookieHeader = await sessionCookieHeader().catch(() => "");

    const emit = (event, data) => {
      if (event === "done") recordUsage(data);
      if (win && !win.isDestroyed()) {
        win.webContents.send("agent:event", { turnId, event, data });
      }
    };

    const options = {
      cwd: agentCwd(),
      abortController,
      cookieHeader,
      llm: loadLlmConfig(),
      connectors: connectorsFor(),
      providers: createProviders({ cookieHeader }),
    };

    drive(emit, options)
      .catch((err) => onError(emit, err))
      .finally(() => turns.delete(turnId));

    return { turnId };
  };

  ipcMain.handle("agent:permission", (ev, { requestId, decision } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const pending = pendingPermissions.get(requestId);
    if (!pending) return { ok: false };
    pendingPermissions.delete(requestId);
    if (decision === "always") permissionGrants.always.add(pending.tool);
    if (decision === "full") permissionGrants.full = true;
    pending.resolve(decision === "deny" ? "deny" : "allow");
    return { ok: true };
  });

  ipcMain.handle("usage:session", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { ...sessionUsage };
  });

  ipcMain.handle("agent:turn", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const turnId = crypto.randomUUID();
    const abortController = new AbortController();
    turns.set(turnId, abortController);
    const cookieHeader = await sessionCookieHeader().catch(() => "");

    const emit = (event, data) => {
      if (event === "done") recordUsage(data);
      if (win && !win.isDestroyed()) {
        win.webContents.send("agent:event", { turnId, event, data });
      }
    };

    const askPermission = ({ tool, input }) =>
      new Promise((resolve) => {
        if (permissionGrants.full || permissionGrants.always.has(tool)) {
          resolve("allow");
          return;
        }
        const requestId = crypto.randomUUID();
        pendingPermissions.set(requestId, { resolve, tool });
        emit("permission", { requestId, tool, input });
      });

    runAgentTurn(payload ?? {}, emit, {
      askPermission,
      cwd: agentCwd(),
      abortController,
      cookieHeader,
      llm: loadLlmConfig(),
      connectors: connectorsFor(),
    })
      .catch((err) => {
        if (!abortController.signal.aborted) {
          emit("done", {
            ok: false,
            costUsd: 0,
            ...errorUsage(err),
            error: err instanceof Error ? err.message : "The agent run failed.",
          });
        }
      })
      .finally(() => turns.delete(turnId));

    return { turnId };
  });

  ipcMain.handle("site:crawl", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await runCrawl({ ...(payload ?? {}), trigger: "user" }, emitCrawl, {
        cookieHeader,
        emitRender,
      });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The crawl could not start." };
    }
  });

  ipcMain.handle("site:crawlToken", (ev, { domain } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { token: crawlToken(domain) };
  });

  ipcMain.handle("site:searchSync", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await runSearchSync(payload ?? {}, emitCrawl, { cookieHeader });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The search-data sync could not start." };
    }
  });

  ipcMain.handle("site:searchSyncStop", (ev, { syncId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: requestSearchSyncStop(syncId) };
  });

  ipcMain.handle("site:trafficSync", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await runTrafficSync(payload ?? {}, emitCrawl, { cookieHeader });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The traffic sync could not start." };
    }
  });

  ipcMain.handle("site:trafficSyncStop", (ev, { syncId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: requestTrafficSyncStop(syncId) };
  });

  ipcMain.handle("site:gaProperties", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return await listGaProperties();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not list properties." };
    }
  });

  ipcMain.handle("site:indexCheck", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await runIndexCheck(payload ?? {}, emitCrawl, { cookieHeader });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The index check could not start." };
    }
  });

  ipcMain.handle("content:checks", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { tools: AVAILABLE_CHECKS };
  });

  ipcMain.handle("content:check", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return { results: await runTextChecks(payload ?? {}, { cookieHeader, modelDir: appDir("models") }) };
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The checks could not run." };
    }
  });

  ipcMain.handle("site:gscProperties", async (ev, { domain } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return await listGscProperties(domain);
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not list properties." };
    }
  });

  ipcMain.handle("site:inspectUrl", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await inspectPageUrl(payload ?? {}, { cookieHeader });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The URL inspection failed." };
    }
  });

  ipcMain.handle("site:crawlStop", (ev, { jobId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: requestCrawlStop(jobId) };
  });

  ipcMain.handle("site:render", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    try {
      return await runRender({ ...(payload ?? {}), trigger: "user" }, emitRender, { cookieHeader });
    } catch (err) {
      return { error: err instanceof Error ? err.message : "The render could not start." };
    }
  });

  ipcMain.handle("site:renderStop", (ev, { jobId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: requestRenderStop(jobId) };
  });

  ipcMain.handle("agent:abort", (ev, turnId) => {
    if (!allowedSender(ev)) return;
    turns.get(turnId)?.abort();
    for (const [id, pending] of pendingPermissions) {
      pending.resolve("deny");
      pendingPermissions.delete(id);
    }
  });

  ipcMain.handle("llm:get", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return describeLlmConfig();
  });
  ipcMain.handle("llm:set", (ev, cfg) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      saveLlmConfig(cfg ?? {});
      return describeLlmConfig();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not save." };
    }
  });

  ipcMain.handle("connectors:list", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return listConnectors();
  });
  ipcMain.handle("connectors:set", (ev, provider, values, secretKeys) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      saveConnector(provider, values ?? {}, secretKeys ?? []);
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not save." };
    }
  });
  ipcMain.handle("connectors:remove", (ev, provider) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    removeConnector(provider);
    return listConnectors();
  });

  const providersFor = async () =>
    createProviders({ cookieHeader: await sessionCookieHeader().catch(() => "") });

  ipcMain.handle("social-signals:search", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const providers = await providersFor();
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    return startSignalsSearch(payload ?? {}, emitSignals, {
      providers,
      llm: loadLlmConfig(),
      cookieHeader,
    });
  });
  ipcMain.handle("social-signals:stop", (ev, { jobId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: stopSignalsSearch(jobId) };
  });
  ipcMain.handle("social-signals:platforms", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const providers = await providersFor();
    return { platforms: await providers.listening.availablePlatforms() };
  });
  ipcMain.handle("leads:run", async (ev, payload) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const providers = await providersFor();
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    return startLeadsRun(payload ?? {}, emitLeads, {
      providers,
      llm: loadLlmConfig(),
      cookieHeader,
    });
  });
  ipcMain.handle("leads:stop", (ev, { jobId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { stopping: stopLeadsRun(jobId) };
  });
  ipcMain.handle("leads:sources", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const providers = await providersFor();
    return { sources: await providers.prospects.availableSources() };
  });

  ipcMain.handle("connectors:connectGsc", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      const { refreshToken } = await connectSearchConsole();
      saveConnector("gsc", { refreshToken }, ["refreshToken"]);
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not connect Search Console." };
    }
  });

  ipcMain.handle("connectors:connectGa4", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      const { refreshToken } = await connectAnalytics();
      saveConnector("ga4", { refreshToken }, ["refreshToken"]);
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not connect Google Analytics." };
    }
  });

  ipcMain.handle("analytics:saveSource", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return saveSource(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not store the file." };
    }
  });
  ipcMain.handle("analytics:checkSession", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return checkSession(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not check the session." };
    }
  });
  ipcMain.handle("analytics:resolvePaths", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return resolvePaths(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not find the files." };
    }
  });
  ipcMain.handle("analytics:readSource", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return readSource(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not read the file." };
    }
  });
  ipcMain.handle("analytics:revealSource", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return revealSource(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not show the file." };
    }
  });
  ipcMain.handle("analytics:exportSource", async (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return await exportSource(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not save the file." };
    }
  });
  ipcMain.handle("analytics:exportText", async (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return await exportText(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not save the file." };
    }
  });
  ipcMain.handle("analytics:deleteSource", (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return deleteSource(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not delete the file." };
    }
  });
}

const REGION_PICKER = `(() => new Promise((resolve) => {
  const overlay = document.createElement("div");
  overlay.style.cssText = "position:fixed;inset:0;z-index:2147483647;cursor:crosshair;background:rgba(0,0,0,0.10)";
  const box = document.createElement("div");
  box.style.cssText = "position:fixed;border:1.5px dashed #fff;outline:1.5px dashed #333;display:none;pointer-events:none";
  overlay.appendChild(box);
  document.documentElement.appendChild(overlay);
  let sx = 0, sy = 0, dragging = false;
  const rectFrom = (e) => ({
    x: Math.min(sx, e.clientX), y: Math.min(sy, e.clientY),
    width: Math.abs(e.clientX - sx), height: Math.abs(e.clientY - sy),
  });
  const done = (rect) => { window.removeEventListener("keydown", onKey, true); overlay.remove(); resolve(rect); };
  const onKey = (e) => { if (e.key === "Escape") { e.stopPropagation(); done(null); } };
  window.addEventListener("keydown", onKey, true);
  overlay.addEventListener("mousedown", (e) => { dragging = true; sx = e.clientX; sy = e.clientY; box.style.display = "block"; });
  overlay.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const r = rectFrom(e);
    Object.assign(box.style, { left: r.x + "px", top: r.y + "px", width: r.width + "px", height: r.height + "px" });
  });
  overlay.addEventListener("mouseup", (e) => {
    const r = rectFrom(e);
    done(r.width > 4 && r.height > 4 ? r : null);
  });
}))()`;

function saveShot(image) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const file = path.join(screenshotDir(), `meelu-shot-${stamp}.png`);
  fs.writeFileSync(file, image.toPNG());
  clipboard.writeImage(image);
  log("screenshot saved:", file);
  const note = new Notification({
    title: "Screenshot saved",
    body: `${path.basename(file)} — also copied to clipboard`,
  });
  note.on("click", () => shell.showItemInFolder(file));
  note.show();
}

async function captureRegion() {
  const rect = await win.webContents.executeJavaScript(REGION_PICKER, true).catch(() => null);
  if (!rect) return;
  await new Promise((r) => setTimeout(r, 120));
  saveShot(await win.webContents.capturePage(rect));
}

function registerScreenshotShortcut() {
  win.webContents.on("before-input-event", (ev, input) => {
    const mod = process.platform === "darwin" ? input.meta : input.control;
    if (input.type !== "keyDown" || !mod || !input.shift) return;
    if (input.key.toLowerCase() !== "s") return;
    ev.preventDefault();
    if (input.alt) {
      void win.webContents.capturePage().then(saveShot);
    } else {
      void captureRegion();
    }
  });
}

function boot() {
  registerAgentIpc();

  win = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1020,
    minHeight: 660,
    title: "Meelu",
    backgroundColor: "#f8f5eb",
    webPreferences: {
      preload: path.join(here, "../preload/index.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      ...(app.isPackaged ? {} : { additionalArguments: ["--meelu-dev-annotator"] }),
    },
  });

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (!url.startsWith(BASE_URL) || url.startsWith(`${BASE_URL}/docs`)) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });
  win.webContents.on("will-navigate", (ev, url) => {
    if (!url.startsWith(BASE_URL) && !url.startsWith("file:")) {
      ev.preventDefault();
      shell.openExternal(url);
    }
  });

  registerScreenshotShortcut();

  if (!app.isPackaged) {
    import("../../dev/annotator/main.js")
      .then(({ registerAnnotator }) =>
        registerAnnotator(win, { baseUrl: BASE_URL, projectRoot: REPO_ROOT }))
      .catch((err) => log("annotator unavailable:", err.message));
  }

  win.webContents.on("did-fail-load", (_ev, code, desc, url, isMainFrame) => {
    if (!isMainFrame || Math.abs(code) === 3) return;
    log(`load failed (${code} ${desc}) — reconnecting`);
    void connect();
  });

  void connect();

  clearOrphanedJobs({ cookieHeader: sessionCookieHeader, log });

  startCrawlSchedule({ cookieHeader: sessionCookieHeader, emit: emitCrawl, log });

  startListeningSchedule({
    cookieHeader: sessionCookieHeader,
    emit: emitSignals,
    log,
    providersFor: async () =>
      createProviders({ cookieHeader: await sessionCookieHeader().catch(() => "") }),
    llm: loadLlmConfig,
  });

  startLeadsSchedule({
    cookieHeader: sessionCookieHeader,
    emit: emitLeads,
    log,
    providersFor: async () =>
      createProviders({ cookieHeader: await sessionCookieHeader().catch(() => "") }),
    llm: loadLlmConfig,
  });


  if (process.env.MEELU_SHOT && !app.isPackaged) {
    setTimeout(async () => {
      const image = await win.webContents.capturePage();
      const fs = await import("node:fs");
      fs.writeFileSync(process.env.MEELU_SHOT, image.toPNG());
      log("shot:", process.env.MEELU_SHOT);
      app.quit();
    }, Number(process.env.MEELU_SHOT_DELAY_MS ?? 6000));
  } else if (process.env.MEELU_AUTOEXIT_MS) {
    setTimeout(() => {
      log("autoexit");
      app.quit();
    }, Number(process.env.MEELU_AUTOEXIT_MS));
  }
}

app.whenReady().then(boot);
app.on("before-quit", () => closeAgentSessions());
app.on("window-all-closed", () => app.quit());
