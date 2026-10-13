import { ENV_DEFAULTS, meeluAuthHeaders } from "../../config.js";
import { apiFetch } from "../../net.js";
import { gaConnected, listProperties, runReport } from "./client.js";

const running = new Map();

const CHUNK_DAYS = 28;
const POST_BATCH_ROWS = 5000;

const REPORTS = [
  {
    report: "totals",
    dimensions: ["date"],
    metrics: [
      "totalUsers",
      "newUsers",
      "sessions",
      "engagedSessions",
      "screenPageViews",
      "userEngagementDuration",
      "keyEvents",
      "totalRevenue",
    ],
    row: (r) => ({
      users: r.totalUsers ?? 0,
      newUsers: r.newUsers ?? 0,
      sessions: r.sessions ?? 0,
      engagedSessions: r.engagedSessions ?? 0,
      pageViews: r.screenPageViews ?? 0,
      engagementSeconds: r.userEngagementDuration ?? 0,
      keyEvents: r.keyEvents ?? 0,
      revenue: r.totalRevenue ?? 0,
    }),
  },
  {
    report: "channels",
    dimensions: ["date", "sessionDefaultChannelGroup", "sessionSource", "sessionMedium"],
    metrics: ["sessions", "totalUsers", "newUsers", "engagedSessions", "keyEvents", "totalRevenue"],
    row: (r) => ({
      channel: String(r.sessionDefaultChannelGroup ?? ""),
      source: String(r.sessionSource ?? ""),
      medium: String(r.sessionMedium ?? ""),
      sessions: r.sessions ?? 0,
      users: r.totalUsers ?? 0,
      newUsers: r.newUsers ?? 0,
      engagedSessions: r.engagedSessions ?? 0,
      keyEvents: r.keyEvents ?? 0,
      revenue: r.totalRevenue ?? 0,
    }),
  },
  {
    report: "landing",
    dimensions: ["date", "landingPage", "sessionDefaultChannelGroup"],
    metrics: ["sessions", "engagedSessions", "keyEvents", "totalRevenue"],
    row: (r) => ({
      landingPage: String(r.landingPage ?? ""),
      channel: String(r.sessionDefaultChannelGroup ?? ""),
      sessions: r.sessions ?? 0,
      engagedSessions: r.engagedSessions ?? 0,
      keyEvents: r.keyEvents ?? 0,
      revenue: r.totalRevenue ?? 0,
    }),
  },
  {
    report: "pages",
    dimensions: ["date", "pagePath"],
    metrics: ["screenPageViews", "activeUsers", "userEngagementDuration", "keyEvents"],
    row: (r) => ({
      pagePath: String(r.pagePath ?? ""),
      views: r.screenPageViews ?? 0,
      users: r.activeUsers ?? 0,
      engagementSeconds: r.userEngagementDuration ?? 0,
      keyEvents: r.keyEvents ?? 0,
    }),
  },
  {
    report: "events",
    dimensions: ["date", "eventName"],
    metrics: ["eventCount", "totalUsers", "keyEvents"],
    row: (r) => ({
      eventName: String(r.eventName ?? ""),
      eventCount: r.eventCount ?? 0,
      users: r.totalUsers ?? 0,
      keyEvents: r.keyEvents ?? 0,
    }),
  },
  {
    report: "geo",
    dimensions: ["date", "country"],
    metrics: ["sessions", "totalUsers", "newUsers", "keyEvents", "totalRevenue"],
    row: (r) => ({
      country: String(r.country ?? ""),
      sessions: r.sessions ?? 0,
      users: r.totalUsers ?? 0,
      newUsers: r.newUsers ?? 0,
      keyEvents: r.keyEvents ?? 0,
      revenue: r.totalRevenue ?? 0,
    }),
  },
  {
    report: "tech",
    dimensions: ["date", "deviceCategory", "operatingSystem", "browser"],
    metrics: ["sessions", "totalUsers"],
    row: (r) => ({
      deviceCategory: String(r.deviceCategory ?? ""),
      os: String(r.operatingSystem ?? ""),
      browser: String(r.browser ?? ""),
      sessions: r.sessions ?? 0,
      users: r.totalUsers ?? 0,
    }),
  },
];

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

export async function stopTrafficSync(params, broadcast, options = {}) {
  const { syncId, siteId } = params ?? {};
  const live = running.get(syncId);
  if (live) {
    live.stop = true;
    return { stopping: true };
  }
  const sync = await api(`/site/traffic/sync-jobs/${syncId}`, {
    method: "PATCH",
    siteId,
    cookieHeader: options.cookieHeader ?? "",
    body: { status: "cancelled" },
  });
  broadcast("traffic:done", { syncId, siteId, ok: true, stopped: true, sync });
  return { stopping: true };
}

export async function listGaProperties() {
  if (!gaConnected()) return { connected: false, accounts: [] };
  return { connected: true, accounts: await listProperties() };
}

export async function runTrafficSync(params, emit, options = {}) {
  const { siteId } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId) throw new Error("A traffic sync needs a website — no siteId was passed.");
  if (!gaConnected()) {
    throw new Error("Google Analytics is not connected on this machine. Connect it from Settings first.");
  }

  const opened = await api("/site/traffic/sync-jobs", {
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

function addDays(day, count) {
  const d = new Date(day);
  d.setUTCDate(d.getUTCDate() + count);
  return d.toISOString().slice(0, 10);
}

function spanDays(from, to) {
  return Math.round((new Date(to).getTime() - new Date(from).getTime()) / 86_400_000) + 1;
}

function isoDay(compact) {
  const raw = String(compact ?? "");
  return /^\d{8}$/.test(raw)
    ? `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`
    : raw;
}

async function drive(syncId, siteId, cookieHeader, broadcast) {
  const emit = (event, data) => broadcast(event, { syncId, siteId, ...data });
  const patch = (body) =>
    api(`/site/traffic/sync-jobs/${syncId}`, { method: "PATCH", siteId, cookieHeader, body });

  let plan;
  try {
    plan = await api(`/site/traffic/sync-jobs/${syncId}/claim`, {
      method: "POST",
      siteId,
      cookieHeader,
    });
  } catch (e) {
    emit("traffic:done", { ok: false, error: readable(e) });
    return;
  }

  try {
    const property = plan.property;
    if (!property) {
      const accounts = await listProperties();
      const message =
        "No Google Analytics property is chosen for this website yet. Pick the property that " +
        "reports on it — Analytics does not say which website a property measures, so it " +
        "cannot be matched automatically.";
      await patch({ status: "failed", error: message });
      emit("traffic:done", { ok: false, needsProperty: true, candidates: accounts, error: message });
      return;
    }

    await patch({ property });
    emit("traffic:started", {
      property,
      daysTotal: plan.daysTotal,
      resumeFrom: plan.resumeFrom,
    });

    let daysDone = 0;
    let rowsStored = 0;
    let stopped = false;

    const post = async (report, rows) => {
      for (let i = 0; i < rows.length; i += POST_BATCH_ROWS) {
        const res = await api("/site/traffic/rows", {
          method: "POST",
          siteId,
          cookieHeader,
          body: { report, rows: rows.slice(i, i + POST_BATCH_ROWS) },
        });
        rowsStored += res.stored ?? 0;
      }
    };

    for (let from = plan.startDay; from <= plan.endDay; from = addDays(from, CHUNK_DAYS)) {
      if (running.get(syncId)?.stop) {
        stopped = true;
        break;
      }
      const last = addDays(from, CHUNK_DAYS - 1);
      const to = last > plan.endDay ? plan.endDay : last;

      for (const spec of REPORTS) {
        if (running.get(syncId)?.stop) {
          stopped = true;
          break;
        }
        const report = await runReport(property, {
          startDate: from,
          endDate: to,
          dimensions: spec.dimensions,
          metrics: spec.metrics,
        });
        const rows = report.map((r) => ({ day: isoDay(r.date), ...spec.row(r) }));
        await post(spec.report, rows);
        emit("traffic:progress", {
          daysDone,
          daysTotal: plan.daysTotal,
          rowsStored,
          day: to,
          report: spec.report,
        });
      }
      if (stopped) break;

      daysDone += spanDays(from, to);
      await patch({ daysDone, rowsStored }).catch(() => undefined);
      emit("traffic:progress", {
        daysDone,
        daysTotal: plan.daysTotal,
        rowsStored,
        day: to,
      });
    }

    const settled = await patch({
      status: stopped ? "cancelled" : "completed",
      daysDone,
      rowsStored,
    });

    emit("traffic:done", { ok: true, stopped, daysDone, rowsStored, sync: settled });
  } catch (e) {
    const message = readable(e);
    await patch({ status: "failed", error: message }).catch(() => undefined);
    emit("traffic:done", { ok: false, error: message });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
