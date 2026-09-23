const TOPIC_INTENTS = new Set(["seeking_tool", "seeking_help"]);
const BRAND_INTENTS = new Set(["complaining", "praising", "recommending"]);
const RECENCY_HALF_DAYS = 14;

function engagementOf(p) {
  return Math.log1p((p.engagement?.score ?? 0) + (p.engagement?.comments ?? 0));
}

export function withScores(posts, mode) {
  const values = posts.map(engagementOf).sort((a, b) => a - b);
  const percentile = (v) => {
    if (values.length <= 1) return 0.5;
    let below = 0;
    for (const x of values) if (x < v) below += 1;
    return below / (values.length - 1);
  };
  const wantedFor = (p) => {
    if (p.kind === "brand" || p.kind === "competitor") return BRAND_INTENTS;
    if (p.kind === "topic") return TOPIC_INTENTS;
    return mode === "brand" ? BRAND_INTENTS : TOPIC_INTENTS;
  };
  const now = Date.now();
  return posts.map((p) => {
    const ageDays = Math.max(0, (now - new Date(p.createdAt).getTime()) / 86_400_000);
    const intentMatch = wantedFor(p).has(p.classification?.intent) ? 1 : 0;
    const compositeScore =
      0.5 * (p.relevanceScore ?? 0) +
      0.25 * intentMatch +
      0.15 * Math.exp(-ageDays / RECENCY_HALF_DAYS) +
      0.1 * percentile(engagementOf(p));
    return { ...p, compositeScore: Math.round(compositeScore * 1000) / 1000 };
  });
}
