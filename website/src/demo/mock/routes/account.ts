import type { ApiKey, CreatedApiKey, Note, NoteHit, NoteKind, SiteProfile, UserProfile } from "@demo/lib/types";
import type { UserPrompt, UserPromptSurface } from "@demo/features/user-prompts/api";
import { activeSiteId } from "@demo/lib/current-site";
import * as siteData from "../data/site";
import * as misc from "../data/misc";
import * as credits from "../data/credits";
import { DEFAULT_MODEL, MODELS } from "../data/llm";
import { USER_PROMPTS } from "../data/prompts";
import { b, MockHttpError, newId, now, num, ok, paginate, type Route } from "../core";
import { NOW, DAY } from "../rand";

const state = {
  sites: [{ ...siteData.SITE, status: "active", pausedAt: null, deletesAt: null }] as SiteProfile[],
  siteAddedAt: new Map<string, number>([[siteData.SITE_ID, NOW - credits.FIRST_SITE_ADDED_MS]]),
  profile: { ...misc.PROFILE } as UserProfile,
  notes: [...misc.NOTES] as Note[],
  keys: [...misc.KEYS] as ApiKey[],
  ledger: [...credits.LEDGER],
  balanceMicros: credits.BALANCE_MICROS,
  payments: [...credits.PAYMENTS],
  defaultModel: DEFAULT_MODEL,
  prompts: [...USER_PROMPTS] as UserPrompt[],
};

export function chargeCredits(kind: credits.LedgerKind, note: string, deltaUsd: number): void {
  const delta = credits.micros(deltaUsd);
  state.balanceMicros += delta;
  state.ledger.unshift({
    id: newId("lg"),
    kind,
    deltaMicros: delta,
    balanceAfterMicros: state.balanceMicros,
    deltaUsd: credits.usd(delta),
    balanceAfterUsd: credits.usd(state.balanceMicros),
    providerCallId: kind === "usage" ? newId("pc") : null,
    note,
    createdAt: now(),
  });
}

export function setSiteSummary(siteId: string, summary: string): void {
  const site = state.sites.find((s) => s.id === siteId);
  if (site) Object.assign(site, { summary, updatedAt: now() });
}

export function siteSummary(siteId: string): string | undefined {
  return state.sites.find((s) => s.id === siteId)?.summary;
}

function currentSite(): SiteProfile {
  const id = activeSiteId() ?? siteData.SITE_ID;
  return state.sites.find((s) => s.id === id) ?? state.sites[0];
}

function siteOrThrow(id: string): SiteProfile {
  const site = state.sites.find((s) => s.id === id);
  if (!site) throw new MockHttpError(404, "Not found");
  return site;
}

function readHost(value: unknown): string {
  const raw = String(value ?? "").trim().toLowerCase();
  const host = raw.replace(/^[a-z]+:\/\//, "").replace(/[/?#].*$/, "");
  if (!host || !host.includes(".") || /\s/.test(host)) {
    throw new MockHttpError(
      422,
      `"${String(value ?? "")}" doesn't look like a website — give the host it actually serves on, such as "www.example.com" or "example.com".`,
    );
  }
  return host;
}

function countryCodes(value: unknown): string[] {
  if (!Array.isArray(value)) throw new MockHttpError(422, "markets must be an array of two-letter country codes.");
  const codes = value.map((v) => String(v ?? "").trim().toUpperCase()).filter(Boolean).map((c) => (c === "UK" ? "GB" : c));
  const bad = codes.filter((c) => !/^[A-Z]{2}$/.test(c));
  if (bad.length) throw new MockHttpError(422, `${bad.join(", ")} is not a two-letter country code such as US or GB.`);
  return [...new Set(codes)];
}

function languageCode(value: unknown): string | null {
  const code = String(value ?? "").trim().toLowerCase();
  if (!code) return null;
  if (!/^[a-z]{2}$/.test(code)) throw new MockHttpError(422, `"${String(value)}" is not a two-letter language code such as en or de.`);
  return code;
}

function applySiteChanges(site: SiteProfile, body: Record<string, unknown>): SiteProfile {
  const changes: Partial<SiteProfile> = {};
  if (body.domain !== undefined && body.domain !== null) {
    const domain = readHost(body.domain);
    const clash = state.sites.find((s) => s.domain === domain && s.id !== site.id);
    if (clash) throw new MockHttpError(409, `${clash.name} already uses ${domain} in this workspace.`);
    changes.domain = domain;
  }
  if (typeof body.name === "string" && body.name.trim()) changes.name = body.name.trim();
  if (body.markets !== undefined && body.markets !== null) changes.markets = countryCodes(body.markets);
  if (body.language !== undefined) changes.language = languageCode(body.language);
  if (typeof body.repoUrl === "string") changes.repoUrl = body.repoUrl;
  if (typeof body.summary === "string") changes.summary = body.summary;
  if (Array.isArray(body.sitemapUrls)) changes.sitemapUrls = body.sitemapUrls.map(String).filter((u) => u.trim());
  if (Array.isArray(body.socialLinks)) changes.socialLinks = body.socialLinks as SiteProfile["socialLinks"];
  Object.assign(site, changes, { updatedAt: now() });
  return site;
}

function siteDayCharges(domain: string) {
  return state.ledger.filter((e) => e.kind === "site_day" && e.note === `${domain} · one day`);
}

function siteBilling(site: SiteProfile): credits.SiteBilling {
  const charges = siteDayCharges(site.domain);
  const earlier = state.sites.findIndex((s) => s.id === site.id);
  const added = state.siteAddedAt.get(site.id) ?? NOW;
  const lastMs = charges.length
    ? Math.max(...charges.map((e) => Date.parse(e.createdAt)))
    : added + Math.max(0, Math.floor((Date.now() - added) / DAY)) * DAY;
  return {
    siteId: site.id,
    status: site.status,
    lastChargedAt: new Date(lastMs).toISOString(),
    nextChargeAt: new Date(lastMs + DAY).toISOString(),
    chargeCount: charges.length + (site.id === siteData.SITE_ID ? credits.TRIAL_DAYS + 1 : 0),
    chargedMicros: charges.reduce((sum, e) => sum - e.deltaMicros, 0),
    dailyPriceMicros: credits.sitePriceMicros(Math.max(0, earlier)),
  };
}

function notesForSite(): Note[] {
  const siteId = activeSiteId() ?? siteData.SITE_ID;
  return state.notes.filter((n) => n.siteId === siteId);
}

function noteText(value: unknown): string {
  const note = String(value ?? "").trim();
  if (!note) throw new MockHttpError(422, "A note needs some text.");
  if (note.length > 4000) {
    throw new MockHttpError(422, `That note is ${note.length} characters — keep it under 4000. A note is a standing rule or a correction, not a document.`);
  }
  return note;
}

function noteKind(value: unknown): NoteKind {
  if (value === undefined || value === null) return "note";
  if (value !== "note" && value !== "feedback") throw new MockHttpError(422, `Invalid kind "${String(value)}". Allowed values: note, feedback.`);
  return value;
}

function promptText(value: unknown, field: string, limit: number): string {
  const text = String(value ?? "").trim();
  if (!text) throw new MockHttpError(422, `A saved prompt needs a ${field}.`);
  if (text.length > limit) throw new MockHttpError(422, `That ${field} is ${text.length} characters — keep it under ${limit}.`);
  return text;
}

function promptSurface(value: unknown): UserPromptSurface {
  if (value === "seo" || value === "structure") return value;
  throw new MockHttpError(422, `Invalid surface "${String(value)}". Allowed values: seo, structure.`);
}

function promptOrThrow(id: string): UserPrompt {
  const prompt = state.prompts.find((p) => p.id === id);
  if (!prompt) throw new MockHttpError(404, "Not found");
  return prompt;
}

function randomHex(length: number): string {
  let out = "";
  for (let i = 0; i < length; i++) out += Math.floor(Math.random() * 16).toString(16);
  return out;
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/site$/, () => ok(currentSite())],
  ["PUT", /^\/api\/v1\/site$/, (_m, _q, body) => ok(applySiteChanges(currentSite(), body))],
  ["PATCH", /^\/api\/v1\/site$/, (_m, _q, body) => ok(applySiteChanges(currentSite(), body))],

  ["GET", /^\/api\/v1\/sites$/, (_m, q) => {
    const needle = q.get("q")?.toLowerCase().trim();
    const status = q.get("status");
    const rows = state.sites.filter(
      (s) =>
        (!needle || `${s.name} ${s.domain}`.toLowerCase().includes(needle)) &&
        (!status || s.status === status),
    );
    return paginate(rows, q);
  }],
  ["POST", /^\/api\/v1\/sites$/, (_m, _q, body) => {
    const domain = readHost(b(body, "domain"));
    const name = String(b(body, "name") ?? "").trim();
    if (!name) throw new MockHttpError(422, "A website needs a name.");
    const clash = state.sites.find((s) => s.domain === domain);
    if (clash) {
      throw new MockHttpError(409, `${clash.name} (${domain}) is already in this workspace — switch to it rather than adding it twice.`);
    }
    const price = credits.usd(credits.sitePriceMicros(state.sites.length));
    const funded = state.balanceMicros >= credits.micros(price);
    const at = now();
    const site: SiteProfile = {
      id: newId("site"),
      createdAt: at,
      updatedAt: at,
      domain,
      name,
      status: funded ? "active" : "disabled",
      pausedAt: funded ? null : at,
      deletesAt: funded ? null : new Date(Date.now() + credits.PAUSED_RETENTION_DAYS * DAY).toISOString(),
      markets: [],
      language: null,
      socialLinks: [],
      sitemapUrls: [],
      lastCrawledAt: null,
      gscProperty: null,
      gaProperty: null,
    };
    state.sites.push(site);
    state.siteAddedAt.set(site.id, Date.now());
    if (funded) chargeCredits("site_day", `${domain} · one day`, -price);
    return ok(site);
  }],
  ["GET", /^\/api\/v1\/sites\/([^/]+)$/, (m) => ok(siteOrThrow(m[1]))],
  ["PUT", /^\/api\/v1\/sites\/([^/]+)$/, (m, _q, body) => ok(applySiteChanges(siteOrThrow(m[1]), body))],
  ["PATCH", /^\/api\/v1\/sites\/([^/]+)$/, (m, _q, body) => ok(applySiteChanges(siteOrThrow(m[1]), body))],
  ["DELETE", /^\/api\/v1\/sites\/([^/]+)$/, (m) => {
    const site = siteOrThrow(m[1]);
    if (site.id === siteData.SITE_ID) {
      throw new MockHttpError(400, "The demo keeps Ledgerly so there is something to look at. Add another website and delete that one instead.");
    }
    state.sites = state.sites.filter((s) => s.id !== site.id);
    state.notes = state.notes.filter((n) => n.siteId !== site.id);
    state.prompts = state.prompts.filter((p) => p.siteId !== site.id);
    return ok({ id: site.id, deleted: true });
  }],

  ["GET", /^\/api\/v1\/profile$/, () => ok(state.profile)],
  ["PUT", /^\/api\/v1\/profile$/, (_m, _q, body) => {
    const fullName = String(body.fullName ?? state.profile.fullName).trim();
    Object.assign(state.profile, body, { fullName: fullName || state.profile.fullName, updatedAt: now() });
    return ok(state.profile);
  }],

  ["GET", /^\/api\/v1\/keys$/, (_m, q) => paginate([...state.keys].sort((a, c) => c.createdAt.localeCompare(a.createdAt)), q)],
  ["POST", /^\/api\/v1\/keys$/, (_m, _q, body) => {
    const raw = `emcp_${randomHex(64)}`;
    const at = now();
    const name = String(b(body, "name") ?? "").trim() || "MCP key";
    const record: ApiKey = { id: newId("key"), createdAt: at, updatedAt: at, name, preview: `${raw.slice(0, 9)}…${raw.slice(-4)}`, lastUsedAt: null };
    state.keys.push(record);
    const created: CreatedApiKey = { ...record, key: raw };
    return ok(created);
  }],
  ["DELETE", /^\/api\/v1\/keys\/([^/]+)$/, (m) => {
    if (!state.keys.some((k) => k.id === m[1])) throw new MockHttpError(404, "Not found");
    state.keys = state.keys.filter((k) => k.id !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],

  ["GET", /^\/api\/v1\/notes$/, (_m, q) => {
    const kinds = q.getAll("kind");
    const pool = notesForSite().filter((n) => kinds.length === 0 || kinds.includes(n.kind));
    const needle = q.get("q")?.toLowerCase().trim();
    if (needle) {
      const terms = needle.split(/\s+/).filter((t) => t.length > 1);
      const hits: NoteHit[] = pool
        .map((n) => ({ ...n, score: terms.filter((t) => n.note.toLowerCase().includes(t)).length / Math.max(1, terms.length), similarity: null }))
        .filter((n) => n.score > 0)
        .sort((a, c) => c.score - a.score)
        .slice(0, num(q.get("limit")) ?? 25);
      return ok({ hits, mode: "keyword", note: hits.length ? null : "No note uses those words." });
    }
    const contains = q.get("contains")?.toLowerCase().trim();
    const rows = pool.filter((n) => !contains || n.note.toLowerCase().includes(contains));
    return paginate([...rows].sort((a, c) => c.createdAt.localeCompare(a.createdAt)), q);
  }],
  ["POST", /^\/api\/v1\/notes$/, (_m, _q, body) => {
    const at = now();
    const note: Note = {
      id: newId("nt"),
      createdAt: at,
      updatedAt: at,
      siteId: activeSiteId() ?? siteData.SITE_ID,
      note: noteText(b(body, "note")),
      kind: noteKind(b(body, "kind")),
    };
    state.notes.unshift(note);
    return ok(note);
  }],
  ["GET", /^\/api\/v1\/notes\/([^/]+)$/, (m) => {
    const note = state.notes.find((n) => n.id === m[1]);
    if (!note) throw new MockHttpError(404, "Not found");
    return ok(note);
  }],
  ...(["PUT", "PATCH"] as const).map((method): Route => [method, /^\/api\/v1\/notes\/([^/]+)$/, (m, _q, body) => {
    const note = state.notes.find((n) => n.id === m[1]);
    if (!note) throw new MockHttpError(404, "Not found");
    if (body.note !== undefined && body.note !== null) note.note = noteText(body.note);
    if (body.kind !== undefined && body.kind !== null) note.kind = noteKind(body.kind);
    note.updatedAt = now();
    return ok(note);
  }]),
  ["DELETE", /^\/api\/v1\/notes\/([^/]+)$/, (m) => {
    if (!state.notes.some((n) => n.id === m[1])) throw new MockHttpError(404, "Not found");
    state.notes = state.notes.filter((n) => n.id !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],

  ["GET", /^\/api\/v1\/credits$/, () => ok({ balanceMicros: state.balanceMicros, balanceUsd: credits.usd(state.balanceMicros) })],
  ["GET", /^\/api\/v1\/credits\/ledger$/, (_m, q) => paginate(state.ledger, q)],
  ["GET", /^\/api\/v1\/credits\/sites\/([^/]+)$/, (m) => ok(siteBilling(siteOrThrow(m[1])))],

  ["GET", /^\/api\/v1\/payments$/, (_m, q) => paginate(state.payments, q)],
  ["GET", /^\/api\/v1\/payments\/([^/]+)$/, (m) => {
    const payment = state.payments.find((p) => p.id === m[1]);
    if (!payment) throw new MockHttpError(404, "Not found");
    return ok(payment);
  }],
  ["POST", /^\/api\/v1\/payments\/checkout$/, (_m, _q, body) => {
    const amount = Number(b(body, "amountUsd"));
    if (!Number.isFinite(amount) || amount < credits.MIN_TOPUP_USD || amount > credits.MAX_TOPUP_USD) {
      throw new MockHttpError(400, `Top-ups must be between $${credits.MIN_TOPUP_USD.toFixed(2)} and $${credits.MAX_TOPUP_USD.toFixed(2)}.`);
    }
    throw new MockHttpError(
      400,
      `Top-ups are switched off in the demo, so nothing was charged. In the Meelu app, $${amount.toFixed(2)} buys $${amount.toFixed(2)} of credits.`,
    );
  }],

  ["GET", /^\/api\/v1\/llm\/models$/, () => ok(MODELS)],
  ["GET", /^\/api\/v1\/llm\/preference$/, () => ok({ defaultModel: state.defaultModel })],
  ["PUT", /^\/api\/v1\/llm\/preference$/, (_m, _q, body) => {
    const id = String(b(body, "defaultModel") ?? "");
    if (!MODELS.some((m) => m.id === id)) throw new MockHttpError(400, `Meelu does not offer the model ${id}.`);
    state.defaultModel = id;
    return ok({ defaultModel: id });
  }],

  ["GET", /^\/api\/v1\/user-prompts$/, (_m, q) => {
    const siteId = activeSiteId() ?? siteData.SITE_ID;
    const surface = q.get("surface");
    const contains = q.get("contains")?.toLowerCase().trim();
    const rows = state.prompts.filter(
      (p) =>
        p.siteId === siteId &&
        (!surface || p.surface === surface) &&
        (!contains || `${p.label} ${p.prompt}`.toLowerCase().includes(contains)),
    );
    return paginate(rows, q);
  }],
  ["POST", /^\/api\/v1\/user-prompts$/, (_m, _q, body) => {
    const at = now();
    const prompt: UserPrompt = {
      id: newId("up"),
      siteId: activeSiteId() ?? siteData.SITE_ID,
      surface: promptSurface(b(body, "surface")),
      label: promptText(b(body, "label"), "name", 80),
      prompt: promptText(b(body, "prompt"), "prompt", 8000),
      createdAt: at,
      updatedAt: at,
    };
    state.prompts.push(prompt);
    return ok(prompt);
  }],
  ["GET", /^\/api\/v1\/user-prompts\/([^/]+)$/, (m) => ok(promptOrThrow(m[1]))],
  ["PATCH", /^\/api\/v1\/user-prompts\/([^/]+)$/, (m, _q, body) => {
    const prompt = promptOrThrow(m[1]);
    if (body.label !== undefined && body.label !== null) prompt.label = promptText(body.label, "name", 80);
    if (body.prompt !== undefined && body.prompt !== null) prompt.prompt = promptText(body.prompt, "prompt", 8000);
    prompt.updatedAt = now();
    return ok(prompt);
  }],
  ["DELETE", /^\/api\/v1\/user-prompts\/([^/]+)$/, (m) => {
    promptOrThrow(m[1]);
    state.prompts = state.prompts.filter((p) => p.id !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],
];
