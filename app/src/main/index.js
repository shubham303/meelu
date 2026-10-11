import { app, BrowserWindow, clipboard, ipcMain, Notification, session, shell } from "electron";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ENV_DEFAULTS, REPO_ROOT, UPDATE_MANIFEST_URL } from "./config.js";
import { startUpdateCheck } from "./update-check.js";
import { connectSearchConsole } from "./integrations/gsc/oauth.js";
import { connectAnalytics } from "./integrations/ga/oauth.js";
import { saveTextFile } from "./save-text-file.js";
import { closeAgentSessions, runAgentTurn } from "./agent/runner.js";
import { requestCrawlStop, runCrawl } from "./crawler/index.js";
import {
  activeSignalsSearch,
  startSignalsSearch,
  stopSignalsSearch,
} from "./social-signals/pipeline.js";
import { startPageReviewSchedule } from "./page-review/index.js";
import { requestRenderStop, runRender } from "./render/index.js";
import { AVAILABLE_CHECKS, runTextChecks } from "./text-checks/index.js";
import { inspectPageUrl, listGscProperties, requestSearchSyncStop, runIndexCheck, runSearchSync } from "./integrations/gsc/sync.js";
import { listGaProperties, requestTrafficSyncStop, runTrafficSync } from "./integrations/ga/sync.js";
import { startCrawlSchedule } from "./crawler/schedule.js";
import { describeSite, startSiteSummarySchedule } from "./site-summary/index.js";
import { createProviders } from "./providers/index.js";
import { clearOrphanedJobs } from "./orphaned-jobs.js";
import { appDir, screenshotDir } from "./paths.js";
import { crawlToken } from "./crawler/token.js";
import { describeLlmConfig, loadLlmConfig, saveLlmConfig } from "./integrations/llm/config.js";
import {
  listConnectors,
  removeConnector,
  saveConnector,
} from "./connector-config.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const BASE_URL = ENV_DEFAULTS.meeluBaseUrl;
const DASH_URL = `${BASE_URL}/dashboard`;
const TRUSTED_ORIGIN = new URL(BASE_URL).origin;
const EXTERNAL_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

let win = null;
let connecting = false;
let updates = { current: () => null };

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

const RECONNECT_EVERY_MS = 2000;

async function showWaiting() {
  if (win.webContents.getURL().startsWith("file:")) return;
  log(`cannot reach ${BASE_URL} — showing the offline screen`);
  try {
    await win.loadFile(path.join(here, "../renderer/waiting.html"), {
      query: app.isPackaged ? {} : { dev: "1" },
    });
  } catch (err) {
    log("offline screen failed to load:", err.message);
  }
}

async function loadDashboard() {
  try {
    await win.loadURL(DASH_URL);
    return true;
  } catch (err) {
    if (err.errno === -3) return true;
    log("dashboard load failed:", err.message);
    return false;
  }
}

async function connect() {
  if (connecting) return;
  connecting = true;
  try {
    while (!win.isDestroyed()) {
      if ((await serverUp()) && !win.isDestroyed() && (await loadDashboard())) {
        log(`dashboard loaded from ${DASH_URL}`);
        return;
      }
      if (win.isDestroyed()) return;
      await showWaiting();
      await new Promise((r) => setTimeout(r, RECONNECT_EVERY_MS));
    }
  } finally {
    connecting = false;
  }
}

function agentCwd() {
  return appDir("agent-workspace");
}

function parsedUrl(url) {
  try {
    return new URL(url);
  } catch {
    return null;
  }
}

function isTrustedUrl(url) {
  return parsedUrl(url)?.origin === TRUSTED_ORIGIN;
}

function opensInMainWindow(url) {
  const parsed = parsedUrl(url);
  return parsed?.origin === TRUSTED_ORIGIN && !parsed.pathname.startsWith("/docs");
}

function openOutside(url) {
  const parsed = parsedUrl(url);
  if (parsed && EXTERNAL_PROTOCOLS.has(parsed.protocol)) void shell.openExternal(parsed.toString());
}

function allowedSender(ev) {
  return isTrustedUrl(ev.senderFrame?.url ?? "");
}

function emitCrawl(event, data) {
  if (win && !win.isDestroyed()) win.webContents.send("crawl:event", { event, data });
}


function emitSignals(message) {
  if (win && !win.isDestroyed()) win.webContents.send("social-signals:event", message);
}

function emitSummary(event, data) {
  if (win && !win.isDestroyed()) win.webContents.send("site-summary:event", { event, data });
}

function emitRender(event, data) {
  if (win && !win.isDestroyed()) win.webContents.send("render:event", { event, data });
}

function emitUpdate(update) {
  if (win && !win.isDestroyed()) win.webContents.send("app:update-event", update);
}

async function sessionCookieHeader() {
  const cookies = await win.webContents.session.cookies.get({ url: BASE_URL });
  return cookies.map((c) => `${c.name}=${c.value}`).join("; ");
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

  ipcMain.handle("app:update", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return { update: updates.current() };
  });

  ipcMain.handle("app:downloadUpdate", (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const update = updates.current();
    if (!update) return { ok: false };
    void shell.openExternal(update.downloadUrl);
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

  ipcMain.handle("site:describe", async (ev, { siteId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const cookieHeader = await sessionCookieHeader().catch(() => "");
    void describeSite(siteId, { cookieHeader, llm: loadLlmConfig(), emit: emitSummary, log });
    return { started: true };
  });

  ipcMain.handle("site:crawlToken", (ev, { domain } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return { token: crawlToken(domain) };
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not create a crawl token." };
    }
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
  ipcMain.handle("connectors:remove", (ev, provider) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      removeConnector(provider);
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not remove." };
    }
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
  ipcMain.handle("social-signals:active", (ev, { siteId } = {}) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    return activeSignalsSearch(siteId);
  });
  ipcMain.handle("social-signals:platforms", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    const providers = await providersFor();
    return { platforms: await providers.listening.availablePlatforms() };
  });

  ipcMain.handle("connectors:connectGsc", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      const { refreshToken } = await connectSearchConsole();
      saveConnector("gsc", { refreshToken });
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not connect Search Console." };
    }
  });

  ipcMain.handle("connectors:connectGa4", async (ev) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      const { refreshToken } = await connectAnalytics();
      saveConnector("ga4", { refreshToken });
      return listConnectors();
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not connect Google Analytics." };
    }
  });

  ipcMain.handle("files:saveText", async (ev, params) => {
    if (!allowedSender(ev)) return { error: "forbidden" };
    try {
      return await saveTextFile(params ?? {});
    } catch (err) {
      return { error: err instanceof Error ? err.message : "Could not save the file." };
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

function lockDownDefaultSession() {
  const ses = session.defaultSession;
  const allowed = (permission, url) =>
    permission === "clipboard-sanitized-write" && isTrustedUrl(url);
  ses.setPermissionRequestHandler((_contents, permission, callback, details) => {
    callback(allowed(permission, details?.requestingUrl ?? ""));
  });
  ses.setPermissionCheckHandler((_contents, permission, requestingOrigin) =>
    allowed(permission, requestingOrigin),
  );
}

function guardNavigation(contents) {
  contents.setWindowOpenHandler(({ url }) => {
    if (opensInMainWindow(url)) {
      void contents.loadURL(url);
    } else {
      openOutside(url);
    }
    return { action: "deny" };
  });
  const keepInside = (ev, url) => {
    if (opensInMainWindow(url)) return;
    ev.preventDefault();
    openOutside(url);
  };
  contents.on("will-navigate", keepInside);
  contents.on("will-redirect", (ev, url, _inPlace, isMainFrame) => {
    if (isMainFrame) keepInside(ev, url);
  });
}

function boot() {
  lockDownDefaultSession();
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
      devTools: !app.isPackaged,
      ...(app.isPackaged ? {} : { additionalArguments: ["--meelu-dev-annotator"] }),
    },
  });

  guardNavigation(win.webContents);

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

  startSiteSummarySchedule({
    cookieHeader: sessionCookieHeader,
    llm: loadLlmConfig,
    emit: emitSummary,
    log,
  });

  startPageReviewSchedule({ cookieHeader: sessionCookieHeader, llm: loadLlmConfig, log });

  updates = startUpdateCheck({
    manifestUrl: UPDATE_MANIFEST_URL,
    currentVersion: app.getVersion(),
    onUpdate: emitUpdate,
    log,
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

if (app.requestSingleInstanceLock()) {
  app.on("second-instance", () => {
    if (!win || win.isDestroyed()) return;
    if (win.isMinimized()) win.restore();
    win.focus();
  });
  app.whenReady().then(boot);
  app.on("before-quit", () => closeAgentSessions());
  app.on("window-all-closed", () => app.quit());
} else {
  app.quit();
}
