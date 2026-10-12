import type { SearchIntent } from "./types";

const BASE_URL = "https://api.dataforseo.com";
const OK = 20000;

export class ProviderError extends Error {
  constructor(
    readonly provider: string,
    message: string,
  ) {
    super(message);
  }
}

export type Spend = { dataforseo: number; openrouter: number };

type Envelope = {
  status_code?: number;
  status_message?: string;
  cost?: number;
  tasks?: Array<{
    status_code?: number;
    status_message?: string;
    result?: unknown[] | null;
  } | null>;
};

async function post(
  path: string,
  task: Record<string, unknown>,
  spend: Spend,
  signal?: AbortSignal,
): Promise<unknown[]> {
  const auth = process.env.DATAFORSEO_AUTH?.trim();
  if (!auth) throw new ProviderError("dataforseo", "DATAFORSEO_AUTH is not set");

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: { authorization: `Basic ${auth}`, "content-type": "application/json" },
      body: JSON.stringify([task]),
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(60_000)]) : AbortSignal.timeout(60_000),
      cache: "no-store",
    });
  } catch (error) {
    throw new ProviderError("dataforseo", `${path}: ${error instanceof Error ? error.message : error}`);
  }

  const body = (await response.json().catch(() => null)) as Envelope | null;
  if (!response.ok || !body) {
    throw new ProviderError("dataforseo", `${path}: HTTP ${response.status}`);
  }
  if (typeof body.cost === "number") spend.dataforseo += body.cost;
  if (body.status_code !== OK) {
    throw new ProviderError("dataforseo", `${path}: ${body.status_code} ${body.status_message ?? ""}`);
  }
  const task0 = body.tasks?.[0];
  if (!task0 || task0.status_code !== OK) {
    throw new ProviderError(
      "dataforseo",
      `${path}: ${task0?.status_code ?? "no task"} ${task0?.status_message ?? ""}`,
    );
  }
  return task0.result ?? [];
}

export type Suggestion = {
  keyword: string;
  coreKeyword: string | null;
  adsVolume: number;
  cpc: number | null;
  searchIntent: SearchIntent | null;
};

type LabsItem = {
  keyword?: string;
  keyword_info?: { search_volume?: number | null; cpc?: number | null } | null;
  keyword_properties?: { core_keyword?: string | null } | null;
  search_intent_info?: { main_intent?: string | null } | null;
};

const INTENTS = new Set(["informational", "navigational", "commercial", "transactional"]);

function toSuggestion(item: LabsItem): Suggestion | null {
  const keyword = item.keyword?.trim().toLowerCase();
  if (!keyword) return null;
  const intent = item.search_intent_info?.main_intent ?? null;
  return {
    keyword,
    coreKeyword: item.keyword_properties?.core_keyword?.trim().toLowerCase() || null,
    adsVolume: item.keyword_info?.search_volume ?? 0,
    cpc: item.keyword_info?.cpc ?? null,
    searchIntent: intent && INTENTS.has(intent) ? (intent as SearchIntent) : null,
  };
}

export async function keywordSuggestions(
  seed: string,
  locale: { locationCode: number; languageCode: string },
  options: { limit: number; minVolume: number },
  spend: Spend,
  signal?: AbortSignal,
): Promise<Suggestion[]> {
  const result = (await post(
    "/v3/dataforseo_labs/google/keyword_suggestions/live",
    {
      keyword: seed,
      location_code: locale.locationCode,
      language_code: locale.languageCode,
      include_seed_keyword: true,
      limit: options.limit,
      filters: [["keyword_info.search_volume", ">=", options.minVolume]],
      order_by: ["keyword_info.search_volume,desc"],
    },
    spend,
    signal,
  )) as Array<{ seed_keyword_data?: LabsItem | null; items?: LabsItem[] | null } | null>;

  const first = result[0];
  const items: LabsItem[] = [...(first?.items ?? [])];
  if (first?.seed_keyword_data) items.unshift(first.seed_keyword_data);
  return items.map(toSuggestion).filter((s): s is Suggestion => s !== null);
}

export async function clickstreamVolumes(
  keywords: string[],
  locale: { locationCode: number; languageCode: string },
  spend: Spend,
  signal?: AbortSignal,
): Promise<Map<string, number>> {
  const result = (await post(
    "/v3/keywords_data/clickstream_data/dataforseo_search_volume/live",
    { keywords, location_code: locale.locationCode, language_code: locale.languageCode },
    spend,
    signal,
  )) as Array<{ items?: Array<{ keyword?: string; search_volume?: number | null }> | null } | null>;

  const volumes = new Map<string, number>();
  for (const item of result[0]?.items ?? []) {
    if (item.keyword && typeof item.search_volume === "number") {
      volumes.set(item.keyword.toLowerCase(), item.search_volume);
    }
  }
  return volumes;
}

export async function organicTop10(
  keyword: string,
  locale: { locationCode: number; languageCode: string },
  spend: Spend,
  signal?: AbortSignal,
): Promise<string[]> {
  const result = (await post(
    "/v3/serp/google/organic/live/regular",
    {
      keyword,
      location_code: locale.locationCode,
      language_code: locale.languageCode,
      depth: 10,
    },
    spend,
    signal,
  )) as Array<{ items?: Array<{ type?: string; rank_group?: number; url?: string }> | null } | null>;

  return (result[0]?.items ?? [])
    .filter((item) => item.type === "organic" && typeof item.url === "string")
    .sort((a, b) => (a.rank_group ?? 0) - (b.rank_group ?? 0))
    .slice(0, 10)
    .map((item) => item.url as string);
}
