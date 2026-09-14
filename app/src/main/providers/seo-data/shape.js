import { DEFAULT_LOCALE } from "./adapter.js";

const MAX_URL = 2048;

const LOCALES = {
  us: DEFAULT_LOCALE,
  usa: DEFAULT_LOCALE,
  "united states": DEFAULT_LOCALE,
  uk: { locationCode: 2826, languageCode: "en" },
  gb: { locationCode: 2826, languageCode: "en" },
  "united kingdom": { locationCode: 2826, languageCode: "en" },
  ca: { locationCode: 2124, languageCode: "en" },
  canada: { locationCode: 2124, languageCode: "en" },
  au: { locationCode: 2036, languageCode: "en" },
  australia: { locationCode: 2036, languageCode: "en" },
  in: { locationCode: 2356, languageCode: "en" },
  india: { locationCode: 2356, languageCode: "en" },
  ie: { locationCode: 2372, languageCode: "en" },
  ireland: { locationCode: 2372, languageCode: "en" },
  nz: { locationCode: 2554, languageCode: "en" },
  "new zealand": { locationCode: 2554, languageCode: "en" },
  sg: { locationCode: 2702, languageCode: "en" },
  singapore: { locationCode: 2702, languageCode: "en" },
  de: { locationCode: 2276, languageCode: "de" },
  germany: { locationCode: 2276, languageCode: "de" },
  fr: { locationCode: 2250, languageCode: "fr" },
  france: { locationCode: 2250, languageCode: "fr" },
  es: { locationCode: 2724, languageCode: "es" },
  spain: { locationCode: 2724, languageCode: "es" },
  it: { locationCode: 2380, languageCode: "it" },
  italy: { locationCode: 2380, languageCode: "it" },
  nl: { locationCode: 2528, languageCode: "nl" },
  netherlands: { locationCode: 2528, languageCode: "nl" },
  br: { locationCode: 2076, languageCode: "pt" },
  brazil: { locationCode: 2076, languageCode: "pt" },
  mx: { locationCode: 2484, languageCode: "es" },
  mexico: { locationCode: 2484, languageCode: "es" },
  jp: { locationCode: 2392, languageCode: "ja" },
  japan: { locationCode: 2392, languageCode: "ja" },
  se: { locationCode: 2752, languageCode: "sv" },
  sweden: { locationCode: 2752, languageCode: "sv" },
};

export function localeOf(input = {}) {
  return {
    locationCode: Number(input.locationCode) || DEFAULT_LOCALE.locationCode,
    languageCode: (input.languageCode || DEFAULT_LOCALE.languageCode).toLowerCase(),
  };
}

export function normalizeKeywords(list) {
  const seen = new Set();
  for (const raw of Array.isArray(list) ? list : []) {
    const keyword = String(raw ?? "")
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
    if (keyword) seen.add(keyword);
  }
  return [...seen];
}

export function chunk(items, size) {
  const out = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

export function ownDomain(domain) {
  const cleaned = String(domain ?? "")
    .trim()
    .toLowerCase()
    .replace(/^[a-z]+:\/\//, "")
    .replace(/[/?#].*$/, "");
  return cleaned.startsWith("www.") ? cleaned.slice(4) : cleaned;
}

export function citedUrls(items) {
  const urls = new Set();
  const walk = (node) => {
    if (Array.isArray(node)) {
      for (const child of node) walk(child);
      return;
    }
    if (!node || typeof node !== "object") return;
    for (const [key, value] of Object.entries(node)) {
      if (key === "url" && typeof value === "string") urls.add(value);
      else walk(value);
    }
  };
  walk(items.filter((item) => item?.type === "ai_overview"));
  return urls;
}

export function pick(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function roundValue(value) {
  const number = pick(value);
  return number == null ? null : Math.floor(number + 0.5);
}

export function competitionIndex(competition) {
  const number = pick(competition);
  return number == null ? null : Math.round(number * 100);
}

export function months(rows) {
  const out = [];
  for (const row of rows ?? []) {
    if (!row || row.search_volume == null || row.year == null || row.month == null) continue;
    out.push({ month: `${row.year}-${String(row.month).padStart(2, "0")}-01`, volume: Math.trunc(row.search_volume) });
  }
  return out;
}

export function cleanUrl(raw) {
  const value = String(raw ?? "").trim();
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:" || !parsed.host) return null;
  } catch {
    return null;
  }
  return value.slice(0, MAX_URL);
}

export function clip(raw, cap) {
  if (raw == null) return null;
  const value = String(raw).trim();
  return value ? value.slice(0, cap) : null;
}

export function byMentionsDesc(a, b) {
  return (b ?? -1) - (a ?? -1);
}

export function factFromOverview(item, at) {
  const info = item.keyword_info ?? null;
  return {
    keyword: item.keyword.trim().toLowerCase(),
    volume: info?.search_volume ?? null,
    competition: info?.competition_level ?? null,
    competitionIndex: competitionIndex(info?.competition),
    cpc: info?.cpc ?? null,
    lowTopOfPageBid: info?.low_top_of_page_bid ?? null,
    highTopOfPageBid: info?.high_top_of_page_bid ?? null,
    difficulty: item.keyword_properties?.keyword_difficulty ?? null,
    intent: item.search_intent_info?.main_intent ?? null,
    volumeFetchedAt: at,
    difficultyFetchedAt: at,
    intentFetchedAt: at,
    months: months(info?.monthly_searches),
  };
}

export function ideaOf(item) {
  return {
    keyword: item.keyword.trim().toLowerCase(),
    volume: item.keyword_info?.search_volume ?? null,
    difficulty: item.keyword_properties?.keyword_difficulty ?? null,
    cpc: item.keyword_info?.cpc ?? null,
    intent: item.search_intent_info?.main_intent ?? null,
  };
}

export function promptOf(item, platform) {
  return {
    question: clip(item.question, 500),
    platform,
    aiSearchVolume: roundValue(item.ai_search_volume),
    citedUrls: (item.sources ?? []).map((s) => cleanUrl(s?.url)).filter(Boolean),
    coMentionedBrands: (item.brand_entities ?? []).map((e) => clip(e?.title, 200)).filter(Boolean),
    firstSeen: clip(item.first_response_at, 64),
    lastSeen: clip(item.last_response_at, 64),
  };
}
