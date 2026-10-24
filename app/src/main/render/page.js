import { BrowserWindow, session } from "electron";
import { createHash } from "node:crypto";
import robotsParserModule from "robots-parser";
import { extract } from "../crawler/extract.js";
import { normalise, sameSite } from "../crawler/url.js";
import { isPublicHost } from "../public-address.js";

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
const DATA_TYPES = new Set(["XHR", "Fetch"]);
const ACTIVE_TYPES = new Set(["Script", "Stylesheet", "XHR", "Fetch", "Document"]);
const PASSIVE_TYPES = new Set(["Image", "Media", "Font"]);
const BEACON_PATH = /collect|beacon|track|log|analytics|pixel/i;
const CORS_MESSAGE = /blocked by CORS policy|No 'Access-Control-Allow-Origin'/i;

const RENDER_LOCALE = "en-US";

const HTML_SCRIPT = "document.documentElement.outerHTML";

const HELPERS = `
  const MAX = 5000;
  const SKIP = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "SVG", "TEMPLATE", "HEAD"]);
  const TRACKING = new Set(["gclid", "fbclid", "msclkid", "mc_cid", "mc_eid", "igshid", "ref", "_hsenc", "_hsmi"]);
  const host = location.hostname.replace(/^www\\./, "").toLowerCase();
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
  const skipped = (el) => !el || SKIP.has(el.tagName) || el.closest("script,style,noscript,svg,template");
  const words = (s) => (s || "").trim().split(/\\s+/).filter(Boolean).length;
  const abs = (href) => {
    try {
      const u = new URL(href, location.href);
      if (u.protocol !== "http:" && u.protocol !== "https:") return null;
      u.hash = "";
      if (u.pathname.length > 1 && u.pathname.endsWith("/")) u.pathname = u.pathname.slice(0, -1);
      return u.toString();
    } catch { return null; }
  };
  const norm = (href) => {
    try {
      const u = new URL(href, location.href);
      if (u.protocol !== "http:" && u.protocol !== "https:") return null;
      u.hash = "";
      u.hostname = u.hostname.toLowerCase();
      for (const key of [...u.searchParams.keys()]) {
        if (key.startsWith("utm_") || TRACKING.has(key)) u.searchParams.delete(key);
      }
      u.searchParams.sort();
      if (u.pathname.length > 1 && u.pathname.endsWith("/")) u.pathname = u.pathname.slice(0, -1);
      return u.toString();
    } catch { return null; }
  };
  const same = (u) => { try { return new URL(u).hostname.replace(/^www\\./, "").toLowerCase() === host; } catch { return false; } };
  const visibleTextNodes = () => {
    const out = [];
    const walker = document.createTreeWalker(document.body || document.documentElement, NodeFilter.SHOW_TEXT);
    let node, scanned = 0;
    while ((node = walker.nextNode()) && scanned < MAX) {
      scanned++;
      const el = node.parentElement;
      if (skipped(el)) continue;
      const text = node.textContent.trim();
      if (!text) continue;
      out.push({ el, text, visible: !hidden(el) });
    }
    return out;
  };
`;

const COMMON_SCRIPT = `
(async () => {
  ${HELPERS}
  const vw = window.innerWidth, vh = window.innerHeight;
  const nodes = visibleTextNodes();
  let visibleWordCount = 0;
  const bodyText = [];
  for (const n of nodes) if (n.visible) { visibleWordCount += words(n.text); bodyText.push(n.text); }

  const h1s = Array.from(document.querySelectorAll("h1")).map((h) => h.textContent.trim());
  const SOFT404 = /\\b(404|not found|page (doesn't|does not|cannot be) (exist|found)|no longer available|oops)\\b/i;
  const soft404Signal = SOFT404.test(document.title || "") || h1s.some((t) => SOFT404.test(t));

  let serviceWorker = false;
  try {
    const regs = navigator.serviceWorker ? await Promise.race([navigator.serviceWorker.getRegistrations(), new Promise((r) => setTimeout(() => r([]), 1000))]) : [];
    serviceWorker = (regs || []).length > 0;
  } catch {}

  const anchors = Array.from(document.querySelectorAll("a")).slice(0, MAX);
  const internal = new Set();
  const external = new Set();
  let hashbangLinks = 0, danglingFragmentLinks = 0;
  const ownPath = location.pathname.replace(/\\/$/, "") + location.search;
  for (const a of anchors) {
    const raw = a.getAttribute("href");
    if (!raw) continue;
    let u;
    try { u = new URL(raw, location.href); } catch { continue; }
    if (u.protocol !== "http:" && u.protocol !== "https:") continue;
    if (same(u.href)) {
      if (raw.includes("#!")) hashbangLinks++;
      const n = norm(u.href);
      if (n) internal.add(n);
      const path = u.pathname.replace(/\\/$/, "") + u.search;
      if (u.hash && u.hash.length > 1 && path === ownPath) {
        let id = "";
        try { id = decodeURIComponent(u.hash.slice(1)); } catch { id = u.hash.slice(1); }
        if (id && !document.getElementById(id) && !document.querySelector('[name="' + CSS.escape(id) + '"]')) danglingFragmentLinks++;
      }
    } else {
      external.add(u.hostname.toLowerCase());
    }
  }

  const NAV_CODE = /location\\.(href|assign|replace)|router\\.(push|navigate)|history\\.pushState/;
  const inNav = (el) => !!el.closest("nav,header,footer,[role=navigation]");
  let uncrawlableAnchors = 0, uncrawlableNavAnchors = 0;
  const uncrawlableSamples = [];
  const flag = (el, href) => {
    uncrawlableAnchors++;
    if (inNav(el)) uncrawlableNavAnchors++;
    if (uncrawlableSamples.length < 10) uncrawlableSamples.push({ tag: el.tagName.toLowerCase(), href: href ?? null, text: (el.textContent || "").trim().slice(0, 80) });
  };
  for (const a of anchors) {
    const raw = a.getAttribute("href");
    if (raw === null) {
      if (a.hasAttribute("id")) continue;
      if (a.hasAttribute("onclick") || a.hasAttribute("role")) flag(a, null);
      continue;
    }
    const t = raw.trim();
    if (/^(mailto|tel):/i.test(t)) continue;
    if (t === "" || t === "#" || /^javascript:/i.test(t) || /^file:/i.test(t)) flag(a, t);
  }
  for (const el of Array.from(document.querySelectorAll("[role=link]:not(a)")).slice(0, MAX)) flag(el, null);
  for (const el of Array.from(document.querySelectorAll("[onclick]:not(a)")).slice(0, MAX)) {
    if (NAV_CODE.test(el.getAttribute("onclick") || "")) flag(el, null);
  }
  const metaFragment = !!document.querySelector('meta[name="fragment"]');

  const LOAD_MORE = /^(load|show|view|see) more/i;
  let loadMoreControl = false;
  for (const el of Array.from(document.querySelectorAll("button, a, [role=button]")).slice(0, MAX)) {
    if (hidden(el) || el.closest("form")) continue;
    if (LOAD_MORE.test((el.textContent || "").trim())) { loadMoreControl = true; break; }
  }
  const PAGINATION = /[?&]page=\\d+|\\/page\\/\\d+/;
  const paginationLinks = !!document.querySelector('link[rel="next"]') ||
    anchors.some((a) => PAGINATION.test(a.getAttribute("href") || ""));

  const images = [];
  let imagesWithoutSrc = 0, imagesWithoutSrcAboveFold = 0;
  for (const img of Array.from(document.querySelectorAll("img")).slice(0, MAX)) {
    const r = img.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const srcAttr = img.getAttribute("src");
    const lazy = img.dataset.src || img.dataset.lazy || img.dataset.original;
    const broken = !srcAttr || (srcAttr.startsWith("data:") && img.naturalWidth <= 1) || (lazy && !img.currentSrc);
    if (broken) {
      imagesWithoutSrc++;
      if (r.top < vh) imagesWithoutSrcAboveFold++;
    }
    if (images.length < 100) {
      const src = abs(img.currentSrc || srcAttr || lazy || "");
      if (src) {
        const entry = { src };
        if (img.hasAttribute("alt")) entry.alt = (img.getAttribute("alt") || "").trim();
        images.push(entry);
      }
    }
  }

  let shadowDomWords = 0, scannedHosts = 0;
  const all = document.querySelectorAll("*");
  for (let i = 0; i < all.length && scannedHosts < MAX; i++) {
    const el = all[i];
    if (!el.shadowRoot) continue;
    scannedHosts++;
    let slotted = 0;
    for (const child of el.children) if (child.assignedSlot) slotted += words(child.textContent);
    shadowDomWords += Math.max(0, words(el.shadowRoot.textContent) - slotted);
  }

  const PLUGIN_TYPE = /application\\/x-(shockwave-flash|silverlight|java)/i;
  const PLUGIN_SRC = /\\.(swf|flv|class|xap)(\\?|$)/i;
  let pluginContent = 0;
  for (const el of document.querySelectorAll("embed, object, applet")) {
    const type = el.getAttribute("type") || "";
    const src = el.getAttribute("src") || el.getAttribute("data") || "";
    if (PLUGIN_TYPE.test(type) || PLUGIN_SRC.test(src)) pluginContent++;
  }

  const head = document.head || document.documentElement;
  const titleCount = head.querySelectorAll("title").length;
  const descriptionCount = document.querySelectorAll('meta[name="description"]').length;
  const canonicalHrefs = Array.from(document.querySelectorAll('link[rel="canonical"]')).map((l) => abs(l.getAttribute("href") || "") || (l.getAttribute("href") || "")).slice(0, 10);
  const canonicalCount = document.querySelectorAll('link[rel="canonical"]').length;
  const robotsMetaContents = Array.from(document.querySelectorAll('meta[name="robots"], meta[name="googlebot"]')).map((m) => (m.getAttribute("content") || "").trim()).slice(0, 10);

  const sorted = (v) => {
    if (Array.isArray(v)) return v.map(sorted);
    if (v && typeof v === "object") { const o = {}; for (const k of Object.keys(v).sort()) o[k] = sorted(v[k]); return o; }
    return v;
  };
  const flatten = (v, depth = 0) => {
    if (depth > 3 || !v || typeof v !== "object") return [];
    if (Array.isArray(v)) return v.flatMap((x) => flatten(x, depth + 1));
    const g = v["@graph"];
    return g ? [v, ...flatten(g, depth + 1)] : [v];
  };
  const blocks = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
  let schemaInvalidBlocks = 0;
  const schemaNodes = [];
  for (const b of blocks) {
    let parsed;
    try { parsed = JSON.parse(b.textContent || ""); } catch { schemaInvalidBlocks++; continue; }
    for (const node of flatten(parsed)) {
      const t = node["@type"];
      const types = typeof t === "string" ? [t] : Array.isArray(t) ? t.map(String) : [];
      if (!types.length || schemaNodes.length >= 60) continue;
      let json = "";
      try { json = JSON.stringify(sorted(node)).slice(0, 20000); } catch { continue; }
      schemaNodes.push({ type: types.join("|"), json });
    }
  }

  const hreflang = {};
  let hreflangInvalid = 0;
  for (const l of document.querySelectorAll('link[rel="alternate"][hreflang]')) {
    const k = (l.getAttribute("hreflang") || "").trim();
    const href = l.getAttribute("href") || "";
    if (!k) continue;
    hreflang[k] = abs(href) || href;
    const lang = k.split("-")[0].toLowerCase();
    const okLang = k.toLowerCase() === "x-default" || /^[a-z]{2,3}$/.test(lang);
    if (!/^https?:/i.test(abs(href) || href) || !okLang) hreflangInvalid++;
  }

  const socialMetaCount = document.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]').length;
  const nosnippetCount = document.querySelectorAll("[data-nosnippet]").length;
  const TOKEN = /\\{\\{[^}]+\\}\\}|\\[\\[[^\\]]+\\]\\]/g;
  const desc = document.querySelector('meta[name="description"]')?.getAttribute("content") || "";
  const headText = [document.title || "", desc, ...h1s].join("\\n");
  const templateTokensHead = (headText.match(TOKEN) || []).length;
  const templateTokensBody = (bodyText.join("\\n").match(TOKEN) || []).length;
  const viewportMeta = document.querySelector('meta[name="viewport"]')?.getAttribute("content") ?? null;

  let overlayCoverage = 0, overlaySample = null;
  const area = vw * vh;
  const center = document.elementFromPoint(Math.floor(vw / 2), Math.floor(vh / 2));
  for (let i = 0; i < all.length && i < MAX * 2; i++) {
    const el = all[i];
    const cs = getComputedStyle(el);
    if (!(cs.position === "fixed" || cs.position === "sticky" || cs.position === "absolute")) continue;
    if (cs.visibility === "hidden" || parseFloat(cs.opacity) <= 0.05) continue;
    const r = el.getBoundingClientRect();
    const ix = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
    const iy = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    const cover = area > 0 ? (ix * iy) / area : 0;
    if (cover < 0.5) continue;
    if (!center || !(el === center || el.contains(center))) continue;
    if (words(el.textContent) < 15) continue;
    if (cover > overlayCoverage) {
      overlayCoverage = Math.round(cover * 100) / 100;
      overlaySample = (el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\\s+/).slice(0, 2).join(".") : "") + " " + (el.textContent || "").trim().slice(0, 100)).slice(0, 200);
    }
  }

  return {
    visibleWordCount, soft404Signal, serviceWorker,
    internalLinkUrls: [...internal].slice(0, 500),
    externalLinkHosts: [...external].slice(0, 100),
    uncrawlableAnchors, uncrawlableNavAnchors, uncrawlableSamples,
    hashbangLinks, metaFragment, danglingFragmentLinks, loadMoreControl, paginationLinks,
    images, imagesWithoutSrc, imagesWithoutSrcAboveFold, shadowDomWords, pluginContent,
    titleCount, descriptionCount, canonicalCount, canonicalHrefs, robotsMetaContents,
    schemaBlocks: blocks.length, schemaInvalidBlocks, schemaNodes,
    hreflang, hreflangInvalid, socialMetaCount, nosnippetCount,
    templateTokensHead, templateTokensBody, viewportMeta, overlayCoverage, overlaySample,
  };
})()
`;

const MOBILE_SCRIPT = `
(() => {
  ${HELPERS}
  const vw = window.innerWidth;
  let hiddenWordCount = 0, textChars = 0, smallChars = 0;
  for (const n of visibleTextNodes()) {
    if (!n.visible) { hiddenWordCount += words(n.text); continue; }
    const len = n.text.length;
    textChars += len;
    const size = parseFloat(getComputedStyle(n.el).fontSize);
    if (Number.isFinite(size) && size < 12) smallChars += len;
  }
  let hiddenInternalLinks = 0;
  for (const a of Array.from(document.querySelectorAll("a[href]")).slice(0, MAX)) {
    let u;
    try { u = new URL(a.getAttribute("href"), location.href); } catch { continue; }
    if (!same(u.href)) continue;
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
  const smallTextRatio = textChars > 0 ? Math.round((smallChars / textChars) * 1000) / 1000 : 0;
  return { hiddenWordCount, hiddenInternalLinks, viewportOverflowPx, smallTapTargets, smallTextRatio, textChars };
})()
`;

const sessions = new Map();
const windows = new Map();

const WEB_PROTOCOLS = new Set(["http:", "https:", "ws:", "wss:"]);
const INLINE_PROTOCOLS = new Set(["data:", "blob:", "about:"]);
const HOST_VERDICT_MS = 60_000;
const HOST_VERDICT_LIMIT = 2_000;
const hostVerdicts = new Map();

async function publicHostCached(hostname) {
  const hit = hostVerdicts.get(hostname);
  if (hit && Date.now() - hit.at < HOST_VERDICT_MS) return hit.ok;
  const ok = await isPublicHost(hostname);
  if (hostVerdicts.size >= HOST_VERDICT_LIMIT) hostVerdicts.clear();
  hostVerdicts.set(hostname, { ok, at: Date.now() });
  return ok;
}

async function requestAllowed(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (INLINE_PROTOCOLS.has(parsed.protocol)) return true;
  if (!WEB_PROTOCOLS.has(parsed.protocol)) return false;
  return publicHostCached(parsed.hostname);
}

function lockDown(ses) {
  ses.setPermissionRequestHandler((_contents, _permission, callback) => callback(false));
  ses.setPermissionCheckHandler(() => false);
  ses.on("will-download", (ev, item) => {
    ev.preventDefault();
    item.cancel();
  });
  ses.webRequest.onBeforeRequest((details, callback) => {
    requestAllowed(details.url).then(
      (ok) => callback({ cancel: !ok }),
      () => callback({ cancel: true }),
    );
  });
}

function partitionSession(device, profile) {
  let ses = sessions.get(device);
  if (!ses) {
    ses = session.fromPartition(`render-pages-${device}`, { cache: false });
    lockDown(ses);
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
  win.webContents.on("will-navigate", (ev, url) => {
    if (!/^https?:$/.test(schemeOf(url) ?? "")) ev.preventDefault();
  });
  win.webContents.setFrameRate(1);
  windows.set(device, { win, reused: 0 });
  return win;
}

async function warm(contents) {
  if (contents.getURL()) return;
  await withTimeout(contents.loadURL("about:blank"), 10_000, "The render window did not start.");
}

let renderQueue = Promise.resolve();

function oneAtATime(work) {
  const turn = renderQueue.then(work, work);
  renderQueue = turn.catch(() => undefined);
  return turn;
}

export function closeWindow() {
  return oneAtATime(() => {
    for (const device of [...windows.keys()]) destroyWindow(device);
  });
}

function hostOf(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return null;
  }
}

function schemeOf(url) {
  try {
    return new URL(url).protocol;
  } catch {
    return null;
  }
}

function pathOf(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return "";
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
  await dbg.sendCommand("Emulation.setLocaleOverride", {}).catch(() => undefined);
  await dbg.sendCommand("Emulation.setLocaleOverride", { locale: RENDER_LOCALE });
}

function schemaHash(node) {
  return createHash("sha256").update(`${node.type}:${node.json}`).digest("hex").slice(0, 16);
}

function number(v, fallback = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function list(v, cap) {
  return Array.isArray(v) ? v.slice(0, cap) : [];
}

function commonFacts(common) {
  if (!common || typeof common !== "object") return {};
  return {
    visibleWordCount: number(common.visibleWordCount),
    soft404Signal: common.soft404Signal === true,
    serviceWorker: common.serviceWorker === true,
    internalLinkUrls: [...new Set(list(common.internalLinkUrls, 500).map((u) => normalise(String(u))))],
    externalLinkHosts: list(common.externalLinkHosts, 100).map(String),
    uncrawlableAnchors: number(common.uncrawlableAnchors),
    uncrawlableNavAnchors: number(common.uncrawlableNavAnchors),
    uncrawlableSamples: list(common.uncrawlableSamples, SAMPLE_LIMIT),
    hashbangLinks: number(common.hashbangLinks),
    metaFragment: common.metaFragment === true,
    danglingFragmentLinks: number(common.danglingFragmentLinks),
    loadMoreControl: common.loadMoreControl === true,
    paginationLinks: common.paginationLinks === true,
    images: list(common.images, 100),
    imagesWithoutSrc: number(common.imagesWithoutSrc),
    imagesWithoutSrcAboveFold: number(common.imagesWithoutSrcAboveFold),
    shadowDomWords: number(common.shadowDomWords),
    pluginContent: number(common.pluginContent),
    titleCount: number(common.titleCount),
    descriptionCount: number(common.descriptionCount),
    canonicalCount: number(common.canonicalCount),
    canonicalHrefs: list(common.canonicalHrefs, 10).map(String),
    robotsMetaContents: list(common.robotsMetaContents, 10).map(String),
    schemaBlocks: number(common.schemaBlocks),
    schemaInvalidBlocks: number(common.schemaInvalidBlocks),
    schemaHashes: list(common.schemaNodes, 60)
      .filter((n) => n && typeof n.type === "string" && typeof n.json === "string")
      .map(schemaHash),
    hreflang: common.hreflang && typeof common.hreflang === "object" && !Array.isArray(common.hreflang) ? common.hreflang : {},
    hreflangInvalid: number(common.hreflangInvalid),
    socialMetaCount: number(common.socialMetaCount),
    nosnippetCount: number(common.nosnippetCount),
    templateTokensHead: number(common.templateTokensHead),
    templateTokensBody: number(common.templateTokensBody),
    viewportMeta: typeof common.viewportMeta === "string" ? common.viewportMeta : null,
    overlayCoverage: number(common.overlayCoverage),
    overlaySample: typeof common.overlaySample === "string" ? common.overlaySample : null,
  };
}

function mobileFacts(mobile) {
  if (!mobile || typeof mobile !== "object") return {};
  return {
    hiddenWordCount: number(mobile.hiddenWordCount),
    hiddenInternalLinks: number(mobile.hiddenInternalLinks),
    viewportOverflowPx: number(mobile.viewportOverflowPx),
    smallTapTargets: number(mobile.smallTapTargets),
    smallTextRatio: number(mobile.smallTextRatio),
    textChars: number(mobile.textChars),
  };
}

export function renderPage(options) {
  return oneAtATime(() => renderOnePage(options));
}

async function renderOnePage({
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
  const pageHost = hostOf(url);
  const pageHttps = schemeOf(url) === "https:";

  const requests = new Map();
  const failed = [];
  const blocked = [];
  const consoleErrors = [];
  const thirdParty = new Set();
  let exceptionCount = 0;
  let corsErrors = 0;
  let jsBytes = 0;
  let totalBytes = 0;
  let lastActivity = Date.now();
  let inFlight = 0;
  let mainFrameId = null;
  let mainDocumentRequestId = null;
  let documentResponses = 0;
  let mainFrameNavigations = 0;
  let status = null;
  let documentBytes = 0;

  const isMainDocument = (params) =>
    params.type === "Document" && (mainFrameId === null || params.frameId === mainFrameId);

  const noteCors = (text) => {
    if (CORS_MESSAGE.test(String(text ?? ""))) corsErrors++;
  };

  const onDebuggerMessage = (_event, method, params) => {
    lastActivity = Date.now();
    if (method === "Page.frameNavigated") {
      if (!params.frame?.parentId) mainFrameId = params.frame.id;
    } else if (method === "Network.requestWillBeSent") {
      const req = params.request;
      const type = params.type ?? "Other";
      const mainDocument = isMainDocument(params);
      if (params.redirectResponse) {
        if (mainDocument) mainFrameNavigations++;
        const prior = requests.get(params.requestId);
        if (prior) prior.done = true;
        inFlight = Math.max(0, inFlight - 1);
      }
      inFlight++;
      const entry = { url: req.url, type, status: null, bytes: 0, error: null, mainDocument };
      requests.set(params.requestId, entry);
      if (mainDocument) mainDocumentRequestId = params.requestId;
      const host = hostOf(req.url);
      if (host && !sameSite(req.url, url) && host !== pageHost) thirdParty.add(host);
      if (robots && sameSite(req.url, url) && req.url !== url && ASSET_TYPES.has(type)) {
        let allowed = true;
        try {
          allowed = robots.isAllowed(req.url, "Googlebot") !== false;
        } catch {
        }
        if (!allowed && blocked.length < SAMPLE_LIMIT) blocked.push({ url: req.url, type });
        if (!allowed) entry.blocked = true;
      }
    } else if (method === "Network.responseReceived") {
      const entry = requests.get(params.requestId);
      if (entry) {
        entry.status = params.response?.status ?? null;
        if (entry.mainDocument && isMainDocument(params)) {
          documentResponses++;
          if (documentResponses > 1) mainFrameNavigations++;
          status = entry.status;
          mainDocumentRequestId = params.requestId;
        }
      }
    } else if (method === "Network.loadingFinished") {
      inFlight = Math.max(0, inFlight - 1);
      const entry = requests.get(params.requestId);
      const bytes = Number(params.encodedDataLength ?? 0);
      totalBytes += bytes;
      if (entry) {
        entry.bytes = bytes;
        entry.done = true;
        if (SCRIPT_TYPES.has(entry.type)) jsBytes += bytes;
        if (params.requestId === mainDocumentRequestId) documentBytes = bytes;
        if (entry.status !== null && entry.status >= 400 && failed.length < SAMPLE_LIMIT) {
          failed.push({ url: entry.url, status: entry.status, type: entry.type });
        }
      }
    } else if (method === "Network.loadingFailed") {
      inFlight = Math.max(0, inFlight - 1);
      const entry = requests.get(params.requestId);
      if (entry) {
        entry.done = true;
        if (!params.canceled) {
          entry.failed = true;
          entry.error = params.errorText ?? "failed";
          if (failed.length < SAMPLE_LIMIT) failed.push({ url: entry.url, error: entry.error, type: entry.type });
        }
      }
      if (params.blockedReason === "cors" || /cors/i.test(params.errorText ?? "")) corsErrors++;
    } else if (method === "Runtime.exceptionThrown") {
      exceptionCount++;
      const text = params.exceptionDetails?.exception?.description ?? params.exceptionDetails?.text ?? "Uncaught exception";
      consoleErrors.push({ level: "exception", text: String(text).slice(0, 300) });
    } else if (method === "Runtime.consoleAPICalled") {
      const text = (params.args ?? [])
        .map((a) => a.value ?? a.description ?? "")
        .join(" ")
        .trim();
      noteCors(text);
      if (params.type === "error") consoleErrors.push({ level: "error", text: text.slice(0, 300) });
    } else if (method === "Log.entryAdded") {
      noteCors(params.entry?.text);
    }
  };

  const onHeaders = (details, callback) => {
    const headers = { ...details.requestHeaders };
    if (crawlToken && sameSite(details.url, url)) headers["x-meelu-crawl"] = crawlToken;
    headers["Accept-Language"] = `${RENDER_LOCALE},en;q=0.9`;
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
        dbg.sendCommand("Page.enable"),
        dbg.sendCommand("Log.enable"),
        dbg.sendCommand("Network.setCacheDisabled", { cacheDisabled: true }),
      ]),
      10_000,
      "The render window did not answer the debugger.",
    );
    await withTimeout(emulate(dbg, device), 10_000, "The render window did not accept the device profile.");

    await withTimeout(ses.clearStorageData(), 10_000, "The render window did not clear its storage.");

    const started = Date.now();
    await withTimeout(
      contents.loadURL(url).catch((e) => {
        if (e?.code === "ERR_ABORTED" || e?.errno === -3) return;
        throw e;
      }),
      PAGE_TIMEOUT_MS,
      "The page did not finish loading in time.",
    );

    let settleReason = "timeout";
    const settleUntil = Date.now() + SETTLE_MAX_MS;
    while (Date.now() < settleUntil) {
      if (inFlight === 0 && Date.now() - lastActivity >= NETWORK_IDLE_MS) {
        settleReason = "idle";
        break;
      }
      await new Promise((r) => setTimeout(r, 200));
    }

    const remaining = Math.max(2_000, PAGE_TIMEOUT_MS - (Date.now() - started));
    const [html, common, mobile] = await withTimeout(
      Promise.all([
        contents.executeJavaScript(HTML_SCRIPT, true),
        contents.executeJavaScript(COMMON_SCRIPT, true).catch(() => null),
        device === "mobile"
          ? contents.executeJavaScript(MOBILE_SCRIPT, true).catch(() => null)
          : Promise.resolve(null),
      ]),
      remaining,
      "The rendered page could not be read in time.",
    );

    const finalUrl = normalise(contents.getURL() || url);
    const rendered = String(html ?? "");
    const facts = extract(rendered, finalUrl, 200);

    const preconnected = new Set();
    for (const match of rendered.matchAll(/<link[^>]+rel=["'](?:preconnect|dns-prefetch)["'][^>]*href=["']([^"']+)["']/gi)) {
      const h = hostOf(match[1].startsWith("//") ? `https:${match[1]}` : match[1]);
      if (h) preconnected.add(h);
    }

    const entries = [...requests.values()];
    const firstParty = (u) => sameSite(u, url) || preconnected.has(hostOf(u) ?? "");
    const isFailed = (e) => e.failed || (e.status !== null && e.status >= 400);
    const dataFailures = entries.filter(
      (e) => DATA_TYPES.has(e.type) && isFailed(e) && firstParty(e.url) && !BEACON_PATH.test(pathOf(e.url)),
    );
    const scriptFailures = entries.filter((e) => e.type === "Script" && isFailed(e) && sameSite(e.url, url));
    const sample = (e) => ({ url: e.url, ...(e.status !== null ? { status: e.status } : {}), ...(e.error ? { error: e.error } : {}) });
    const pending = entries.filter((e) => !e.done);
    const largest = entries
      .filter((e) => e.type === "Script" || e.type === "Stylesheet")
      .reduce((best, e) => (e.bytes > (best?.bytes ?? -1) ? e : best), null);
    const mixed = (types) =>
      pageHttps ? entries.filter((e) => types.has(e.type) && schemeOf(e.url) === "http:").length : 0;

    return {
      ok: true,
      device,
      html: rendered,
      finalUrl,
      status,
      documentBytes,
      htmlBytes: Buffer.byteLength(rendered, "utf8"),
      settleReason,
      pendingRequests: pending.length,
      pendingSamples: pending.slice(0, SAMPLE_LIMIT).map((e) => ({ url: e.url, type: e.type })),
      mainFrameNavigations,
      exceptionCount,
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
      failedRequests: entries.filter(isFailed).length,
      failedSamples: failed,
      blockedAssets: entries.filter((r) => r.blocked).length,
      blockedSamples: blocked,
      jsBytes,
      totalBytes,
      requestCount: requests.size,
      thirdPartyHosts: [...thirdParty].slice(0, 50),
      failedDataRequests: dataFailures.length,
      failedDataSamples: dataFailures.slice(0, SAMPLE_LIMIT).map(sample),
      failedScripts: scriptFailures.length,
      failedScriptSamples: scriptFailures.slice(0, SAMPLE_LIMIT).map(sample),
      corsErrors,
      websocketUsed: entries.some((e) => e.type === "WebSocket"),
      mixedContentActive: mixed(ACTIVE_TYPES),
      mixedContentPassive: mixed(PASSIVE_TYPES),
      largestResourceBytes: largest?.bytes ?? 0,
      largestResourceUrl: largest?.url ?? null,
      ...commonFacts(common),
      ...mobileFacts(mobile),
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
