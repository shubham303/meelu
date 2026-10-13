import { ENV_DEFAULTS, meeluAuthHeaders } from "../../config.js";
import { apiFetch } from "../../net.js";
import {
  gscConnected,
  inspectUrl,
  listProperties,
  matchingProperties,
  searchAnalyticsDay,
} from "./client.js";

const running = new Map();

const POST_BATCH_DAYS = 14;
const HEARTBEAT_EVERY_DAYS = 7;
const INSPECT_PER_RUN = 300;

function api(path, { method = "GET", body, siteId, cookieHeader, allow = [] } = {}) {
  const headers = {
    ...meeluAuthHeaders(cookieHeader),
    ...(body ? { "content-type": "application/json" } : {}),
    ...(siteId ? { "x-meelu-site": siteId } : {}),
  };
  return apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method,
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  }).then(async (res) => {
    const json = await res.json().catch(() => ({}));
    if (!res.ok && !allow.includes(res.status)) {
      throw new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
    }
    return json?.data ?? json;
  });
}

export async function stopSearchSync(params, broadcast, options = {}) {
  const { syncId, siteId } = params ?? {};
  const live = running.get(syncId);
  if (live) {
    live.stop = true;
    return { stopping: true };
  }
  const sync = await api(`/site/search-data/sync-jobs/${syncId}`, {
    method: "PATCH",
    siteId,
    cookieHeader: options.cookieHeader ?? "",
    body: { status: "cancelled" },
  });
  broadcast("search:done", { syncId, siteId, ok: true, stopped: true, sync });
  return { stopping: true };
}

let indexCheck = null;

export async function runIndexCheck(params, emit, options = {}) {
  const { siteId, limit = 300 } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId) throw new Error("An index check needs a website — no siteId was passed.");
  if (!gscConnected()) {
    throw new Error("Search Console is not connected on this machine. Connect it from Settings first.");
  }
  if (indexCheck) throw new Error("An index check is already running.");

  const site = await api("/site", { siteId, cookieHeader });
  if (!site.gscProperty) {
    throw new Error(
      "No Search Console property is chosen for this website yet. Run the search-data sync " +
        "once — it records which property is authoritative.",
    );
  }

  const targets = await api(`/site/search-data/inspections?limit=${limit}`, { siteId, cookieHeader });
  const urls = targets.urls ?? [];
  if (urls.length === 0) {
    emit("index:done", { siteId, ok: true, inspected: 0, note: "Every page already has an index state." });
    return { started: false, inspected: 0 };
  }

  indexCheck = { stop: false };
  void (async () => {
    const inspections = [];
    let note = null;
    try {
      for (const url of urls) {
        if (indexCheck?.stop) break;
        try {
          inspections.push(await inspectUrl(site.gscProperty, url));
        } catch (e) {
          note = `Stopped early: ${readable(e)}`;
          break;
        }
        if (inspections.length % 25 === 0) {
          emit("index:progress", { siteId, inspected: inspections.length, total: urls.length });
        }
      }
      if (inspections.length > 0) {
        await api("/site/search-data/inspections", {
          method: "POST",
          siteId,
          cookieHeader,
          body: { inspections },
        });
      }
      emit("index:done", { siteId, ok: true, inspected: inspections.length, note });
    } catch (e) {
      emit("index:done", { siteId, ok: false, inspected: inspections.length, error: readable(e) });
    } finally {
      indexCheck = null;
    }
  })();

  return { started: true, total: urls.length };
}

export async function inspectPageUrl(params, options = {}) {
  const { siteId, url } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId || !url) throw new Error("Inspecting a URL needs both a website and the URL.");
  if (!gscConnected()) {
    throw new Error("Search Console is not connected on this machine. Connect it from Settings first.");
  }

  const site = await api("/site", { siteId, cookieHeader });
  if (!site.gscProperty) {
    throw new Error(
      "No Search Console property is chosen for this website yet. Run the search-data sync " +
        "once — it records which property is authoritative.",
    );
  }

  const inspection = await inspectUrl(site.gscProperty, url);
  await api("/site/search-data/inspections", {
    method: "POST",
    siteId,
    cookieHeader,
    body: { inspections: [inspection] },
  });
  return { inspection };
}

export async function listGscProperties(domain) {
  if (!gscConnected()) return { connected: false, properties: [], matching: [] };
  const properties = await listProperties();
  return {
    connected: true,
    properties,
    matching: domain ? matchingProperties(domain)(properties) : [],
  };
}

export async function runSearchSync(params, emit, options = {}) {
  const { siteId } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId) throw new Error("A search-data sync needs a website — no siteId was passed.");
  if (!gscConnected()) {
    throw new Error("Search Console is not connected on this machine. Connect it from Settings first.");
  }

  const opened = await api("/site/search-data/sync-jobs", {
    method: "POST",
    siteId,
    cookieHeader,
    body: { trigger: "user" },
    allow: [409],
  });
  if (!opened.started) {
    return { syncId: opened.sync?.id ?? null, started: false, reason: opened.reason };
  }

  const syncId = opened.sync.id;
  running.set(syncId, { stop: false });
  void drive(syncId, siteId, cookieHeader, emit).finally(() => running.delete(syncId));
  return { syncId, siteId, started: true };
}

function nextDay(day) {
  const d = new Date(day);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

async function drive(syncId, siteId, cookieHeader, broadcast) {
  const emit = (event, data) => broadcast(event, { syncId, siteId, ...data });
  const patch = (body) =>
    api(`/site/search-data/sync-jobs/${syncId}`, { method: "PATCH", siteId, cookieHeader, body });

  let plan;
  try {
    plan = await api(`/site/search-data/sync-jobs/${syncId}/claim`, {
      method: "POST",
      siteId,
      cookieHeader,
    });
  } catch (e) {
    emit("search:done", { ok: false, error: readable(e) });
    return;
  }

  let property = plan.property;
  const notes = [];

  try {
    if (!property) {
      const properties = await listProperties();
      const matches = matchingProperties(plan.domain)(properties);
      if (matches.length === 1) {
        property = matches[0].siteUrl;
        await api("/site/search-data/property", {
          method: "POST",
          siteId,
          cookieHeader,
          body: { property },
        });
      } else {
        const message =
          matches.length === 0
            ? `No Search Console property matches ${plan.domain}. This Google account can read: ` +
              `${properties.map((p) => p.siteUrl).join(", ") || "none"}.`
            : `${plan.domain} matches more than one property (${matches
                .map((m) => m.siteUrl)
                .join(", ")}). They are different properties and report different numbers — pick one.`;
        await patch({ status: "failed", error: message });
        emit("search:done", {
          ok: false,
          needsProperty: true,
          candidates: matches.length ? matches : properties,
          error: message,
        });
        return;
      }
    }

    await patch({ property });
    emit("search:started", { property, daysTotal: plan.daysTotal, resumeFrom: plan.resumeFrom });

    let daysDone = 0;
    let rowsStored = 0;
    let pending = [];
    let stopped = false;

    const flush = async () => {
      if (pending.length === 0) return;
      const batch = pending;
      pending = [];
      const res = await api("/site/search-data/rows", {
        method: "POST",
        siteId,
        cookieHeader,
        body: { days: batch },
      });
      rowsStored += res.rows ?? 0;
    };

    for (let day = plan.startDay; day <= plan.endDay; day = nextDay(day)) {
      if (running.get(syncId)?.stop) {
        stopped = true;
        break;
      }
      const rows = await searchAnalyticsDay(property, day);
      pending.push({ day, rows });
      daysDone += 1;
      if (pending.length >= POST_BATCH_DAYS) await flush();
      if (daysDone % HEARTBEAT_EVERY_DAYS === 0) {
        await patch({ daysDone, rowsStored }).catch(() => undefined);
        emit("search:progress", {
          phase: "days",
          daysDone,
          daysTotal: plan.daysTotal,
          rowsStored,
          day,
        });
      }
    }
    await flush();

    let pagesInspected = 0;
    if (!stopped) {
      const targets = await api(`/site/search-data/inspections?limit=${INSPECT_PER_RUN}`, {
        siteId,
        cookieHeader,
      }).catch(() => ({ urls: [] }));
      const urls = targets.urls ?? [];
      const inspections = [];
      for (const url of urls) {
        if (running.get(syncId)?.stop) {
          stopped = true;
          break;
        }
        try {
          inspections.push(await inspectUrl(property, url));
        } catch (e) {
          notes.push(`Index inspection stopped early: ${readable(e)}`);
          break;
        }
        pagesInspected += 1;
        if (pagesInspected % 25 === 0) {
          emit("search:progress", { phase: "inspect", pagesInspected, pagesTotal: urls.length });
        }
      }
      if (inspections.length > 0) {
        await api("/site/search-data/inspections", {
          method: "POST",
          siteId,
          cookieHeader,
          body: { inspections },
        });
      }
    }

    const settled = await patch({
      status: stopped ? "cancelled" : "completed",
      daysDone,
      rowsStored,
      pagesInspected,
      notes,
    });

    emit("search:done", {
      ok: true,
      stopped,
      daysDone,
      rowsStored,
      pagesInspected,
      notes,
      sync: settled,
    });
  } catch (e) {
    const message = readable(e);
    await patch({ status: "failed", error: message }).catch(() => undefined);
    emit("search:done", { ok: false, error: message });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
