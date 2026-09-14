import { BrowserWindow, session } from "electron";
import robotsParserModule from "robots-parser";
import { extract } from "../crawler/extract.js";
import { normalise, sameSite } from "../crawler/url.js";

const robotsParser = robotsParserModule.default ?? robotsParserModule;

export const USER_AGENTS = {
  desktop: {
    googlebot:
      "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Googlebot/2.1; +http://www.google.com/bot.html) Chrome/120.0.0.0 Safari/537.36 MeeluSEO/1.0",
    generic:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 MeeluSEO/1.0",
    ai_bot: "Mozilla/5.0 (compatible; GPTBot/1.2; +https://openai.com/gptbot) MeeluSEO/1.0",
  },
  mobile: {
    googlebot:
      "Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    generic:
      "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 MeeluSEO/1.0",
    ai_bot:
      "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36 (compatible; GPTBot/1.2; +https://openai.com/gptbot) MeeluSEO/1.0",
  },
};

const DEVICES = {
  desktop: { width: 1366, height: 900, deviceScaleFactor: 1, mobile: false },
  mobile: { width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true },
};

const PAGE_TIMEOUT_MS = 45_000;
const NETWORK_IDLE_MS = 1_500;
const SETTLE_MAX_MS = 12_000;
const SAMPLE_LIMIT = 10;
const WINDOW_REUSE = 25;
const SCRIPT_TYPES = new Set(["Script"]);
const ASSET_TYPES = new Set(["Script", "Stylesheet", "Font", "Image", "Fetch", "XHR", "Document", "Other", "Media"]);

const HTML_SCRIPT = "document.documentElement.outerHTML";

const MOBILE_SCRIPT = `
(() => {
  const MAX = 5000;
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "SVG", "TEMPLATE", "HEAD"]);
  const vw = window.innerWidth;
  const hiddenCache = new Map();
  const hidden = (el) => {
    if (!el || el === document.documentElement) return false;
    if (hiddenCache.has(el)) return hiddenCache.get(el);
    let out = false;
    if (el.getAttribute && el.getAttribute("aria-hidden") === "true") out = true;
    else {
      const cs = getComputedStyle(el);
      if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") out = true;
      else {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) out = true;
        else out = hidden(el.parentElement);
      }
    }
    hiddenCache.set(el, out);
    return out;
  };
  let scanned = 0;
  let hiddenWordCount = 0;
  const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode()) && scanned < MAX) {
    scanned++;
    const el = node.parentElement;
    if (!el || SKIP.has(el.tagName) || el.closest("script,style,noscript,svg,template")) continue;
    const text = node.textContent.trim();
    if (!text) continue;
    if (hidden(el)) hiddenWordCount += text.split(/\s+/).length;
  }
  const host = location.hostname.replace(/^www\./, "");
  let hiddenInternalLinks = 0;
  const anchors = Array.from(document.querySelectorAll("a[href]")).slice(0, MAX);
  for (const a of anchors) {
    let u;
    try { u = new URL(a.getAttribute("href"), location.href); } catch { continue; }
    if (u.hostname.replace(/^www\./, "") !== host) continue;
    if (hidden(a)) hiddenInternalLinks++;
  }
  const targets = Array.from(document.querySelectorAll("a, button, [role=button], input[type=submit]")).slice(0, MAX);
  const rects = [];
  for (const t of targets) {
    if (hidden(t)) continue;
    const r = t.getBoundingClientRect();
    rects.push({ x: r.left, y: r.top, w: r.width, h: r.height });
  }
  let smallTapTargets = 0;
  for (let i = 0; i < rects.length; i++) {
    const a = rects[i];
    if (a.w >= 48 && a.h >= 48) continue;
    let crowded = false;
    for (let j = 0; j < rects.length && !crowded; j++) {
      if (i === j) continue;
      const b = rects[j];
      const dx = Math.max(0, Math.max(a.x, b.x) - Math.min(a.x + a.w, b.x + b.w));
      const dy = Math.max(0, Math.max(a.y, b.y) - Math.min(a.y + a.h, b.y + b.h));
      if (dx < 8 && dy < 8) crowded = true;
    }
    if (crowded) smallTapTargets++;
  }
  const viewportOverflowPx = Math.max(0, document.documentElement.scrollWidth - vw);
  return { hiddenWordCount, hiddenInternalLinks, viewportOverflowPx, smallTapTargets };
})()
`;

const sessions = new Map();
const windows = new Map();

function partitionSession(device, profile) {
  let ses = sessions.get(device);
  if (!ses) {
    ses = session.fromPartition(`render-pages-${device}`, { cache: false });
    sessions.set(device, ses);
  }
  const agents = USER_AGENTS[device] ?? USER_AGENTS.desktop;
  ses.setUserAgent(agents[profile] ?? agents.googlebot);
  return ses;
}

function destroyWindow(device) {
  const live = windows.get(device);
  windows.delete(device);
  if (!live || live.win.isDestroyed()) return;
  try {
    live.win.webContents.debugger.detach();
  } catch {
  }
  live.win.destroy();
}

async function windowFor(device, profile) {
  const live = windows.get(device);
  if (live && !live.win.isDestroyed() && live.reused < WINDOW_REUSE) {
    live.reused++;
    partitionSession(device, profile);
    return live.win;
  }
  if (live) {
    destroyWindow(device);
    await new Promise((r) => setTimeout(r, 300));
  }
  const size = DEVICES[device] ?? DEVICES.desktop;
  const win = new BrowserWindow({
    show: false,
    width: size.width,
    height: size.height,
    webPreferences: {
      session: partitionSession(device, profile),
      offscreen: true,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      images: true,
      backgroundThrottling: false,
    },
  });
  win.webContents.setAudioMuted(true);
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.setFrameRate(1);
  windows.set(device, { win, reused: 0 });
  return win;
}

async function warm(contents) {
  if (contents.getURL()) return;
  await withTimeout(contents.loadURL("about:blank"), 10_000, "The render window did not start.");
}

export function closeWindow() {
  for (const device of [...windows.keys()]) destroyWindow(device);
}

function hostOf(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

function robotsFor(robotsTxt, origin) {
  if (!robotsTxt) return null;
  try {
    return robotsParser(`${origin}/robots.txt`, robotsTxt);
  } catch {
    return null;
  }
}

function withTimeout(promise, ms, message) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(message)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

async function emulate(dbg, device) {
  const size = DEVICES[device] ?? DEVICES.desktop;
  if (size.mobile) {
    await dbg.sendCommand("Emulation.setDeviceMetricsOverride", {
      width: size.width,
      height: size.height,
      deviceScaleFactor: size.deviceScaleFactor,
      mobile: true,
    });
    await dbg.sendCommand("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  } else {
    await dbg.sendCommand("Emulation.clearDeviceMetricsOverride").catch(() => undefined);
    await dbg.sendCommand("Emulation.setTouchEmulationEnabled", { enabled: false }).catch(() => undefined);
  }
}

export async function renderPage({
  url,
  device = "desktop",
  profile = "googlebot",
  crawlToken = null,
  robotsTxt = null,
}) {
  if (!DEVICES[device]) device = "desktop";
  const target = await windowFor(device, profile);
  const contents = target.webContents;
  const ses = contents.session;
  const origin = new URL(url).origin;
  const robots = robotsFor(robotsTxt, origin);

  const requests = new Map();
  const failed = [];
  const blocked = [];
  const consoleErrors = [];
  const thirdParty = new Set();
  let jsBytes = 0;
  let totalBytes = 0;
  let lastActivity = Date.now();
  let inFlight = 0;

  const onDebuggerMessage = (_event, method, params) => {
    lastActivity = Date.now();
    if (method === "Network.requestWillBeSent") {
      const req = params.request;
      inFlight++;
      requests.set(params.requestId, { url: req.url, type: params.type ?? "Other", status: null });
      const host = hostOf(req.url);
      if (host && !sameSite(req.url, url) && host !== hostOf(url)) thirdParty.add(host);
      if (robots && sameSite(req.url, url) && req.url !== url && ASSET_TYPES.has(params.type ?? "Other")) {
        let allowed = true;
        try {
          allowed = robots.isAllowed(req.url, "Googlebot") !== false;
        } catch {
        }
        if (!allowed && blocked.length < SAMPLE_LIMIT) blocked.push({ url: req.url, type: params.type ?? "Other" });
        if (!allowed) requests.get(params.requestId).blocked = true;
      }
    } else if (method === "Network.responseReceived") {
      const entry = requests.get(params.requestId);
      if (entry) entry.status = params.response?.status ?? null;
    } else if (method === "Network.loadingFinished") {
      inFlight = Math.max(0, inFlight - 1);
      const entry = requests.get(params.requestId);
      const bytes = Number(params.encodedDataLength ?? 0);
      totalBytes += bytes;
      if (entry && SCRIPT_TYPES.has(entry.type)) jsBytes += bytes;
      if (entry && entry.status !== null && entry.status >= 400 && failed.length < SAMPLE_LIMIT) {
        failed.push({ url: entry.url, status: entry.status, type: entry.type });
      }
      if (entry) entry.done = true;
    } else if (method === "Network.loadingFailed") {
      inFlight = Math.max(0, inFlight - 1);
      const entry = requests.get(params.requestId);
      if (entry && !params.canceled) {
        entry.failed = true;
        if (failed.length < SAMPLE_LIMIT) failed.push({ url: entry.url, error: params.errorText ?? "failed", type: entry.type });
      }
      if (entry) entry.done = true;
    } else if (method === "Runtime.exceptionThrown") {
      const text = params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "Uncaught exception";
      consoleErrors.push({ level: "exception", text: String(text).slice(0, 300) });
    } else if (method === "Runtime.consoleAPICalled" && params.type === "error") {
      const text = (params.args ?? [])
        .map((a) => a.value ?? a.description ?? "")
        .join(" ")
        .trim();
      consoleErrors.push({ level: "error", text: text.slice(0, 300) });
    }
  };

  const onHeaders = (details, callback) => {
    const headers = { ...details.requestHeaders };
    if (crawlToken && sameSite(details.url, url)) headers["x-meelu-crawl"] = crawlToken;
    headers["Accept-Language"] = "en-US,en;q=0.9";
    callback({ requestHeaders: headers });
  };

  ses.webRequest.onBeforeSendHeaders(onHeaders);

  const dbg = contents.debugger;
  try {
    await warm(contents);
    if (!dbg.isAttached()) dbg.attach("1.3");
    dbg.on("message", onDebuggerMessage);
    await withTimeout(
      Promise.all([
        dbg.sendCommand("Network.enable"),
        dbg.sendCommand("Runtime.enable"),
        dbg.sendCommand("Network.setCacheDisabled", { cacheDisabled: true }),
      ]),
      10_000,
      "The render window did not answer the debugger.",
    );
    await withTimeout(emulate(dbg, device), 10_000, "The render window did not accept the device profile.");

    const started = Date.now();
    await withTimeout(
      contents.loadURL(url).catch((e) => {
        if (e?.code === "ERR_ABORTED" || e?.errno === -3) return;
        throw e;
      }),
      PAGE_TIMEOUT_MS,
      "The page did not finish loading in time.",
    );

    const settleUntil = Date.now() + SETTLE_MAX_MS;
    while (Date.now() < settleUntil) {
      if (inFlight === 0 && Date.now() - lastActivity >= NETWORK_IDLE_MS) break;
      await new Promise((r) => setTimeout(r, 200));
    }

    const remaining = Math.max(2_000, PAGE_TIMEOUT_MS - (Date.now() - started));
    const [html, mobile] = await withTimeout(
      Promise.all([
        contents.executeJavaScript(HTML_SCRIPT, true),
        device === "mobile"
          ? contents.executeJavaScript(MOBILE_SCRIPT, true).catch(() => null)
          : Promise.resolve(null),
      ]),
      remaining,
      "The rendered page could not be read in time.",
    );

    const finalUrl = normalise(contents.getURL() || url);
    const facts = extract(String(html ?? ""), finalUrl, 200);
    const uniqueRequests = requests.size;

    return {
      ok: true,
      device,
      html: String(html ?? ""),
      finalUrl,
      title: facts.title,
      metaDescription: facts.metaDescription,
      canonical: facts.canonical,
      h1: facts.h1,
      robotsDirectives: facts.robotsDirectives,
      wordCount: facts.wordCount,
      internalLinks: new Set(facts.outLinks.map((l) => l.url)).size,
      schemaTypes: facts.schemaTypes,
      contentHash: facts.contentHash,
      consoleErrors: consoleErrors.length,
      consoleSamples: consoleErrors.slice(0, SAMPLE_LIMIT),
      failedRequests: [...requests.values()].filter((r) => r.failed || (r.status !== null && r.status >= 400)).length,
      failedSamples: failed,
      blockedAssets: [...requests.values()].filter((r) => r.blocked).length,
      blockedSamples: blocked,
      jsBytes,
      totalBytes,
      requestCount: uniqueRequests,
      thirdPartyHosts: [...thirdParty].slice(0, 50),
      ...(mobile && typeof mobile === "object"
        ? {
            hiddenWordCount: Number(mobile.hiddenWordCount ?? 0),
            hiddenInternalLinks: Number(mobile.hiddenInternalLinks ?? 0),
            viewportOverflowPx: Number(mobile.viewportOverflowPx ?? 0),
            smallTapTargets: Number(mobile.smallTapTargets ?? 0),
          }
        : {}),
    };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  } finally {
    ses.webRequest.onBeforeSendHeaders(null);
    if (contents.isDestroyed()) {
      destroyWindow(device);
    } else {
      dbg.removeListener("message", onDebuggerMessage);
      try {
        await withTimeout(contents.loadURL("about:blank"), 10_000, "");
      } catch {
        destroyWindow(device);
      }
    }
  }
}
