const RECENCY_HALF_DAYS = 14;

function engagementOf(p) {
  return Math.log1p((p.engagement?.score ?? 0) + (p.engagement?.comments ?? 0));
}

export function withScores(posts) {
  const values = posts.map(engagementOf).sort((a, b) => a - b);
  const percentile = (v) => {
    if (values.length <= 1) return 0.5;
    let below = 0;
    for (const x of values) if (x < v) below += 1;
    return below / (values.length - 1);
  };
  const now = Date.now();
  return posts.map((p) => {
    const posted = new Date(p.postedAt ?? p.createdAt ?? "").getTime();
    const ageDays = Number.isFinite(posted) ? Math.max(0, (now - posted) / 86_400_000) : 30;
    const compositeScore =
      0.6 * (p.relevance ?? 0) +
      0.25 * Math.exp(-ageDays / RECENCY_HALF_DAYS) +
      0.15 * percentile(engagementOf(p));
    return { ...p, compositeScore: Math.round(compositeScore * 1000) / 1000 };
  });
}
