export const PROVIDER_CATALOG = [
  {
    id: "dataforseo",
    domain: "seo-data",
    name: "DataForSEO",
    blurb: "Search volume, keyword ideas, SERP snapshots, rankings, Lighthouse and LLM mentions.",
    docsUrl: "https://dataforseo.com/apis",
    fields: [
      { key: "login", label: "API login", secret: false, url: "https://dataforseo.com/apis" },
      { key: "password", label: "API password", secret: true },
    ],
  },
  {
    id: "postproxy",
    domain: "social",
    name: "Postproxy",
    blurb: "Schedule and publish to connected social accounts through your own Postproxy key.",
    docsUrl: "https://postproxy.dev/docs",
    fields: [
      { key: "apiKey", label: "API key", secret: true, url: "https://postproxy.dev" },
    ],
  },
];

export const PROVIDER_DOMAINS = {
  "seo-data": { label: "search data" },
  social: { label: "social publishing" },
};

export function providerEntry(id) {
  return PROVIDER_CATALOG.find((e) => e.id === id) ?? null;
}

export function secretKeys(id) {
  return (providerEntry(id)?.fields ?? []).filter((f) => f.secret).map((f) => f.key);
}
