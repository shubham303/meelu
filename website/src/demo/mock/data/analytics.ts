import type { AnalyticsChat, AnalyticsChatMessage, Report } from "@demo/lib/types";
import { ago, DAY, HOUR, NOW, seeded } from "../rand";
import { SITE_ID } from "./site";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function day(daysAgo: number): string {
  const d = new Date(NOW - daysAgo * DAY);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

function fmt(n: number): string {
  return Math.round(n).toLocaleString("en-US");
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

const CSS = `
*{box-sizing:border-box}
body{margin:0;padding:28px 32px 36px;font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;color:#1c1917;background:#fff}
h1{font-size:21px;line-height:1.3;margin:0 0 4px;font-weight:650;letter-spacing:-.01em}
h2{font-size:15px;margin:28px 0 10px;font-weight:620}
p{margin:0 0 10px;color:#44403c}
.meta{color:#78716c;font-size:12.5px;margin-bottom:22px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:0 0 8px}
.kpi{border:1px solid #e7e5e4;border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:20px;font-weight:650;letter-spacing:-.01em}
.kpi span{font-size:12px;color:#78716c}
.up{color:#15803d}.down{color:#b91c1c}
table{width:100%;border-collapse:collapse;font-size:13px;margin:6px 0 4px}
th{text-align:left;font-weight:600;color:#57534e;border-bottom:1px solid #d6d3d1;padding:7px 8px;font-size:12px}
td{border-bottom:1px solid #f0efed;padding:7px 8px;vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.chart{border:1px solid #e7e5e4;border-radius:10px;padding:14px 12px 8px;margin:6px 0 4px}
.chart svg{display:block;width:100%;height:auto}
.legend{display:flex;gap:16px;font-size:12px;color:#57534e;margin:4px 6px 4px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.note{background:#f5f5f4;border-radius:8px;padding:10px 12px;font-size:12.5px;color:#57534e;margin-top:8px}
.trust{display:inline-block;font-size:11px;font-weight:600;border-radius:999px;padding:2px 8px;margin-left:6px;vertical-align:2px}
.trust.high{background:#dcfce7;color:#166534}.trust.moderate{background:#fef3c7;color:#92400e}
ul{margin:0 0 10px;padding-left:20px;color:#44403c}
li{margin-bottom:4px}
.source{margin-top:26px;padding-top:12px;border-top:1px solid #e7e5e4;font-size:12px;color:#78716c}
`;

function page(title: string, meta: string, body: string): string {
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(title)}</title><style>${CSS}</style></head><body><h1>${esc(title)}</h1><div class="meta">${meta}</div>${body}</body></html>`;
}

function hbar(rows: { label: string; value: number; note?: string }[], color = "#0f766e", unit = ""): string {
  const max = Math.max(...rows.map((r) => r.value));
  const rowH = 30;
  const left = 230;
  const width = 640;
  const barW = width - left - 70;
  const h = rows.length * rowH + 6;
  const bars = rows
    .map((r, i) => {
      const y = i * rowH + 4;
      const w = Math.max(2, (r.value / max) * barW);
      return `<text x="${left - 10}" y="${y + 15}" text-anchor="end" font-size="12" fill="#44403c">${esc(r.label)}</text><rect x="${left}" y="${y + 3}" width="${w.toFixed(1)}" height="17" rx="3" fill="${color}"/><text x="${(left + w + 6).toFixed(1)}" y="${y + 15}" font-size="12" fill="#1c1917" font-weight="600">${r.value.toFixed(1)}${unit}</text>`;
    })
    .join("");
  return `<div class="chart"><svg viewBox="0 0 ${width} ${h}" xmlns="http://www.w3.org/2000/svg">${bars}</svg></div>`;
}

interface LineSpec {
  values: (number | null)[];
  ticks: [number, string][];
  color?: string;
  forecast?: { mid: number[]; lo: number[]; hi: number[] };
  marker?: { index: number; label: string };
  shade?: { from: number; to: number; label: string };
  baseline?: { from: number; to: number; value: number; label: string }[];
}

function lineChart(spec: LineSpec, width = 680, height = 240): string {
  const pad = { l: 46, r: 14, t: 16, b: 28 };
  const n = spec.values.length + (spec.forecast?.mid.length ?? 0);
  const all = [
    ...spec.values.filter((v): v is number => v !== null),
    ...(spec.forecast?.hi ?? []),
  ];
  const rawMax = Math.max(...all);
  const step = rawMax > 2000 ? 1000 : rawMax > 400 ? 100 : 50;
  const yMax = Math.ceil((rawMax * 1.08) / step) * step;
  const x = (i: number) => pad.l + (i / (n - 1)) * (width - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - v / yMax) * (height - pad.t - pad.b);
  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map((f) => {
      const v = yMax * f;
      return `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" stroke="#f0efed"/><text x="${pad.l - 8}" y="${(y(v) + 4).toFixed(1)}" text-anchor="end" font-size="11" fill="#a8a29e">${fmt(v)}</text>`;
    })
    .join("");
  const ticks = spec.ticks
    .map(([i, label]) => `<text x="${x(i).toFixed(1)}" y="${height - 8}" text-anchor="${i === 0 ? "start" : i === n - 1 ? "end" : "middle"}" font-size="11" fill="#a8a29e">${label}</text>`)
    .join("");
  const path = spec.values
    .map((v, i) => (v === null ? "" : `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`))
    .join("");
  const color = spec.color ?? "#0f766e";
  let extra = "";
  if (spec.shade) {
    extra += `<rect x="${x(spec.shade.from).toFixed(1)}" y="${pad.t}" width="${(x(spec.shade.to) - x(spec.shade.from)).toFixed(1)}" height="${height - pad.t - pad.b}" fill="#fef3c7" opacity=".55"/><text x="${(x(spec.shade.from) + 6).toFixed(1)}" y="${pad.t + 12}" font-size="11" fill="#92400e">${spec.shade.label}</text>`;
  }
  for (const seg of spec.baseline ?? []) {
    extra += `<line x1="${x(seg.from).toFixed(1)}" x2="${x(seg.to).toFixed(1)}" y1="${y(seg.value).toFixed(1)}" y2="${y(seg.value).toFixed(1)}" stroke="#78716c" stroke-width="1.5" stroke-dasharray="5 4"/><text x="${((x(seg.from) + x(seg.to)) / 2).toFixed(1)}" y="${(y(seg.value) - 6).toFixed(1)}" text-anchor="middle" font-size="11" fill="#57534e">${seg.label}</text>`;
  }
  if (spec.forecast) {
    const off = spec.values.length - 1;
    const f = spec.forecast;
    const top = f.hi.map((v, i) => `${x(off + i + 1).toFixed(1)},${y(v).toFixed(1)}`);
    const bottom = f.lo.map((v, i) => `${x(off + i + 1).toFixed(1)},${y(v).toFixed(1)}`).reverse();
    const last = spec.values[off] ?? 0;
    const start = `${x(off).toFixed(1)},${y(last).toFixed(1)}`;
    extra += `<polygon points="${[start, ...top, ...bottom].join(" ")}" fill="${color}" opacity=".12"/>`;
    extra += `<polyline points="${[start, ...f.mid.map((v, i) => `${x(off + i + 1).toFixed(1)},${y(v).toFixed(1)}`)].join(" ")}" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="6 4"/>`;
    extra += `<line x1="${x(off).toFixed(1)}" x2="${x(off).toFixed(1)}" y1="${pad.t}" y2="${height - pad.b}" stroke="#d6d3d1"/><text x="${(x(off) + 6).toFixed(1)}" y="${pad.t + 12}" font-size="11" fill="#78716c">forecast</text>`;
  }
  if (spec.marker) {
    const mx = x(spec.marker.index).toFixed(1);
    extra += `<line x1="${mx}" x2="${mx}" y1="${pad.t}" y2="${height - pad.b}" stroke="#b91c1c" stroke-width="1.5" stroke-dasharray="3 3"/><text x="${(Number(mx) + 6).toFixed(1)}" y="${pad.t + 12}" font-size="11" fill="#b91c1c" font-weight="600">${spec.marker.label}</text>`;
  }
  return `<div class="chart"><svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">${grid}${extra}<path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round"/>${ticks}</svg></div>`;
}

const CHANGE_DAY = 23;
const SPAN = 90;

const dailyClicks: number[] = (() => {
  const rng = seeded(4127);
  return Array.from({ length: SPAN }, (_, i) => {
    const daysAgo = SPAN - i;
    const trend = 520 + i * 1.6;
    const weekday = new Date(NOW - daysAgo * DAY).getUTCDay();
    const weekly = weekday === 0 || weekday === 6 ? 0.72 : 1.06;
    const shift = daysAgo <= CHANGE_DAY ? 0.84 : 1;
    return Math.round(trend * weekly * shift * (0.94 + rng() * 0.12));
  });
})();

const before = dailyClicks.slice(SPAN - CHANGE_DAY - 28, SPAN - CHANGE_DAY);
const after = dailyClicks.slice(SPAN - CHANGE_DAY);
const avg = (xs: number[]) => xs.reduce((s, v) => s + v, 0) / xs.length;
const BEFORE_AVG = avg(before);
const AFTER_AVG = avg(after);
const CHANGE_PCT = ((AFTER_AVG - BEFORE_AVG) / BEFORE_AVG) * 100;

const clickTicks: [number, string][] = [0, 15, 30, 45, 60, 75, 89].map((i) => [i, day(SPAN - i)]);

const clicksChart = (compact = false) =>
  lineChart(
    {
      values: dailyClicks,
      ticks: clickTicks,
      marker: { index: SPAN - CHANGE_DAY, label: `changepoint ${day(CHANGE_DAY)}` },
      baseline: [
        { from: SPAN - CHANGE_DAY - 28, to: SPAN - CHANGE_DAY - 1, value: BEFORE_AVG, label: `${fmt(BEFORE_AVG)}/day` },
        { from: SPAN - CHANGE_DAY, to: SPAN - 1, value: AFTER_AVG, label: `${fmt(AFTER_AVG)}/day` },
      ],
    },
    compact ? 600 : 680,
    compact ? 200 : 240,
  );

const weeklyClicks: number[] = (() => {
  const weeks: number[] = [];
  for (let i = SPAN % 7; i + 7 <= SPAN; i += 7) weeks.push(dailyClicks.slice(i, i + 7).reduce((s, v) => s + v, 0));
  return weeks;
})();

const FORECAST = (() => {
  const last = weeklyClicks[weeklyClicks.length - 1];
  const mid = Array.from({ length: 8 }, (_, i) => Math.round(last * (1 + 0.012 * (i + 1)) * (i === 6 || i === 7 ? 0.93 : 1)));
  const lo = mid.map((v, i) => Math.round(v * (1 - 0.05 - i * 0.012)));
  const hi = mid.map((v, i) => Math.round(v * (1 + 0.05 + i * 0.012)));
  return { mid, lo, hi };
})();

const FORECAST_TOTAL = FORECAST.mid.reduce((s, v) => s + v, 0);
const FORECAST_LO = FORECAST.lo.reduce((s, v) => s + v, 0);
const FORECAST_HI = FORECAST.hi.reduce((s, v) => s + v, 0);

const forecastChart = (compact = false) => {
  const w = weeklyClicks.length;
  const ticks: [number, string][] = [
    [0, day(SPAN - (SPAN % 7))],
    [Math.floor(w / 2), day(SPAN - (SPAN % 7) - Math.floor(w / 2) * 7)],
    [w - 1, "this week"],
    [w + 3, `+4 wk`],
    [w + 7, `+8 wk`],
  ];
  return lineChart({ values: weeklyClicks, ticks, forecast: FORECAST }, compact ? 600 : 680, compact ? 210 : 240);
};

const SECTIONS = [
  { label: "Comparisons (/compare)", sessions: 6420, signups: 141 },
  { label: "Tools (/tools)", sessions: 12750, signups: 118 },
  { label: "Templates (/templates)", sessions: 38900, signups: 302 },
  { label: "Blog: invoicing & getting paid", sessions: 21300, signups: 96 },
  { label: "Blog: tax", sessions: 27800, signups: 71 },
  { label: "Blog: everything else", sessions: 15100, signups: 19 },
].map((s) => ({ ...s, rate: (s.signups / s.sessions) * 1000 }));

const sectionsTable = SECTIONS.map(
  (s) => `| ${s.label} | ${fmt(s.sessions)} | ${s.signups} | ${s.rate.toFixed(1)} |`,
).join("\n");

const LOSING_QUERIES = [
  { q: "invoice template", page: "/templates/invoice", impr: [41200, 56900], clicks: [2510, 2210], pos: [3.1, 3.3] },
  { q: "quarterly estimated taxes", page: "/blog/quarterly-estimated-taxes-explained", impr: [18400, 24100], clicks: [930, 780], pos: [4.2, 4.0] },
  { q: "freelance hourly rate calculator", page: "/tools/hourly-rate-calculator", impr: [9800, 13600], clicks: [1040, 910], pos: [2.4, 2.6] },
  { q: "how to invoice as a freelancer", page: "/blog/how-to-invoice-as-a-freelancer", impr: [12100, 15300], clicks: [610, 540], pos: [5.0, 5.4] },
  { q: "1099-nec due date", page: "/blog/1099-nec-guide", impr: [7600, 11900], clicks: [420, 365], pos: [3.8, 3.7] },
];

const queriesTable = LOSING_QUERIES.map((r) => {
  const ctr0 = (r.clicks[0] / r.impr[0]) * 100;
  const ctr1 = (r.clicks[1] / r.impr[1]) * 100;
  const di = ((r.impr[1] - r.impr[0]) / r.impr[0]) * 100;
  const dc = ((r.clicks[1] - r.clicks[0]) / r.clicks[0]) * 100;
  return { ...r, ctr0, ctr1, di, dc };
});

const sign = (v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`;

const SIGNUP_REPORT = page(
  "Which site sections drive trial signups",
  `Last 90 days · first-touch landing page · ledgerly.app <span class="trust moderate">moderate confidence</span>`,
  `<div class="kpis">
<div class="kpi"><b>${fmt(SECTIONS.reduce((s, r) => s + r.signups, 0))}</b><span>trial signups from organic landings</span></div>
<div class="kpi"><b>22.0</b><span>signups per 1k sessions on /compare</span></div>
<div class="kpi"><b>8.5×</b><span>/compare vs the tax blog, per visit</span></div>
</div>
<h2>Signups per 1,000 organic sessions</h2>
${hbar(SECTIONS.map((s) => ({ label: s.label, value: s.rate })))}
<h2>The numbers behind it</h2>
<table><thead><tr><th>Section</th><th class="n">Organic sessions</th><th class="n">Trial signups</th><th class="n">per 1k</th><th class="n">Share of signups</th></tr></thead><tbody>
${SECTIONS.map((s) => `<tr><td>${s.label}</td><td class="n">${fmt(s.sessions)}</td><td class="n">${s.signups}</td><td class="n">${s.rate.toFixed(1)}</td><td class="n">${((s.signups / 747) * 100).toFixed(0)}%</td></tr>`).join("")}
</tbody></table>
<h2>What it means</h2>
<ul>
<li><b>Templates bring the most signups in total</b> (302, 40%) because they bring the most traffic, but a visitor there converts at 7.8 per 1k.</li>
<li><b>Comparison pages convert best by far.</b> Six pages, 5% of organic sessions, 19% of signups. Readers there are already choosing software.</li>
<li><b>The tax blog is large and converts poorly</b> (2.6 per 1k). It earns links and trust, not trials. That is not a reason to cut it.</li>
</ul>
<div class="note">Attribution is first-touch: the signup is credited to the landing page of the session that started it. A visitor who read a tax post last week and came back through /pricing is credited to /pricing, which is excluded here. The gap between /compare and the blog is large enough that this choice does not change the order.</div>
<div class="source">Source: GA4 sessions and the <code>trial_started</code> key event, joined to the site's page sections in the workspace table <code>section_signups_90d</code>. Organic search sessions only.</div>`,
);

const CLICKS_REPORT = page(
  `Organic clicks fell ${Math.abs(CHANGE_PCT).toFixed(0)}% from ${day(CHANGE_DAY)}`,
  `Search Console · last ${SPAN} days · ledgerly.app <span class="trust high">high confidence</span>`,
  `<div class="kpis">
<div class="kpi"><b>${fmt(BEFORE_AVG)}</b><span>clicks/day, 4 weeks before</span></div>
<div class="kpi"><b>${fmt(AFTER_AVG)}</b><span>clicks/day since ${day(CHANGE_DAY)}</span></div>
<div class="kpi"><b class="down">${CHANGE_PCT.toFixed(1)}%</b><span>change in level</span></div>
</div>
<h2>Daily organic clicks with the detected changepoint</h2>
${clicksChart()}
<div class="legend"><span><i style="background:#0f766e"></i>Clicks per day</span><span><i style="background:#78716c"></i>Mean before / after</span><span><i style="background:#b91c1c"></i>Changepoint</span></div>
<h2>Pages that account for the drop</h2>
<table><thead><tr><th>Page</th><th class="n">Clicks/day before</th><th class="n">after</th><th class="n">Change</th><th class="n">Avg position before → after</th></tr></thead><tbody>
<tr><td>/compare/quickbooks</td><td class="n">58</td><td class="n">31</td><td class="n down">−47%</td><td class="n">3.2 → 6.1</td></tr>
<tr><td>/compare/freshbooks</td><td class="n">34</td><td class="n">22</td><td class="n down">−35%</td><td class="n">4.0 → 5.8</td></tr>
<tr><td>/blog/quickbooks-alternatives</td><td class="n">27</td><td class="n">16</td><td class="n down">−41%</td><td class="n">5.1 → 8.3</td></tr>
<tr><td>/templates/invoice</td><td class="n">96</td><td class="n">87</td><td class="n down">−9%</td><td class="n">3.1 → 3.3</td></tr>
<tr><td>/tools/tax-estimator</td><td class="n">21</td><td class="n">29</td><td class="n up">+38%</td><td class="n">7.4 → 4.9</td></tr>
</tbody></table>
<h2>What it means</h2>
<ul>
<li>The drop is a <b>step, not a slide</b>: one changepoint, flat on both sides. That points at a ranking change on a few pages, not at seasonality.</li>
<li>Three comparison pages lost 2–3 positions on the same day and explain most of the lost clicks. They are also the pages that convert best.</li>
<li>The tax estimator gained ground in the same window, which is why the total did not fall further.</li>
</ul>
<div class="note">Suggestion for you to judge: look at what now ranks above /compare/quickbooks for "quickbooks alternative". If the new results are fresher comparison tables, the page's pricing table (last updated in March) is the first thing worth checking. Nothing on the site has been changed.</div>
<div class="source">Source: Search Console page × day rows, shaped into <code>gsc_daily_clicks</code>; changepoint detection (PELT, weekly seasonality removed); weekends are visible as the regular dips.</div>`,
);

const FORECAST_REPORT = page(
  "Organic clicks forecast, next 8 weeks",
  `Search Console weekly clicks · ${weeklyClicks.length} weeks of history · ledgerly.app <span class="trust moderate">moderate confidence</span>`,
  `<div class="kpis">
<div class="kpi"><b>${fmt(FORECAST_TOTAL)}</b><span>expected clicks, next 8 weeks</span></div>
<div class="kpi"><b>${fmt(FORECAST_LO)}–${fmt(FORECAST_HI)}</b><span>80% interval</span></div>
<div class="kpi"><b class="up">+1.2%</b><span>expected growth per week</span></div>
</div>
<h2>Weekly organic clicks and forecast</h2>
${forecastChart()}
<div class="legend"><span><i style="background:#0f766e"></i>Actual</span><span><i style="background:#0f766e;opacity:.3"></i>Forecast with 80% interval</span></div>
<h2>Week by week</h2>
<table><thead><tr><th>Week</th><th class="n">Expected</th><th class="n">Low</th><th class="n">High</th></tr></thead><tbody>
${FORECAST.mid.map((v, i) => `<tr><td>+${i + 1} wk${i >= 6 ? " (holiday dip)" : ""}</td><td class="n">${fmt(v)}</td><td class="n">${fmt(FORECAST.lo[i])}</td><td class="n">${fmt(FORECAST.hi[i])}</td></tr>`).join("")}
</tbody></table>
<div class="note">The model starts from the level after the ${day(CHANGE_DAY)} drop, so it does not assume the comparison pages recover. If they regain their positions, expect the upper half of the band. History is ${weeklyClicks.length} weeks, too short to learn a yearly pattern; the late-year dip comes from last year's Search Console totals and is the least certain part.</div>
<div class="source">Source: <code>gsc_weekly_clicks</code> (Search Console, all pages), additive trend + weekly model; holdout error on the last 4 weeks was 4.6%.</div>`,
);

const QUERIES_REPORT = page(
  "Queries gaining impressions but losing clicks",
  `Search Console · last 28 days vs the 28 before · ledgerly.app <span class="trust high">high confidence</span>`,
  `<p>Five queries where Google shows Ledgerly more often but fewer people click. Position barely moved on any of them, so the lost clicks are not a ranking problem.</p>
<table><thead><tr><th>Query</th><th>Page</th><th class="n">Impressions</th><th class="n">Clicks</th><th class="n">CTR</th><th class="n">Position</th></tr></thead><tbody>
${queriesTable.map((r) => `<tr><td><b>${r.q}</b></td><td>${r.page}</td><td class="n up">${sign(r.di)}</td><td class="n down">${sign(r.dc)}</td><td class="n">${r.ctr0.toFixed(1)}% → ${r.ctr1.toFixed(1)}%</td><td class="n">${r.pos[0]} → ${r.pos[1]}</td></tr>`).join("")}
</tbody></table>
<h2>Click-through rate, before and after</h2>
${hbar(queriesTable.flatMap((r) => [{ label: `${r.q} · before`, value: r.ctr0 }, { label: `${r.q} · now`, value: r.ctr1 }]), "#0e7490", "%")}
<h2>What it means</h2>
<ul>
<li>Four of the five are question-shaped or "template" queries where Google now often answers on the results page. Fewer clicks at the same position is what that looks like.</li>
<li>The titles on these pages are generic. A title that promises something the answer box cannot give (a filled example, a download, a calculator) is worth testing on one page first.</li>
</ul>
<div class="source">Source: Search Console query × page rows for two 28-day windows, in <code>gsc_query_compare_28d</code>; queries with fewer than 5,000 impressions left out.</div>`,
);

export const REPORTS: Report[] = [
  { id: "rp_signups", createdAt: ago(9 * DAY + 2 * HOUR), updatedAt: ago(9 * DAY + 2 * HOUR), siteId: SITE_ID, desk: "analytics", title: "Which site sections drive trial signups", html: SIGNUP_REPORT, createdBy: "agent" },
  { id: "rp_clicks", createdAt: ago(3 * DAY + 5 * HOUR), updatedAt: ago(2 * DAY + 1 * HOUR), siteId: SITE_ID, desk: "analytics", title: `Organic clicks changepoint, ${day(CHANGE_DAY)}`, html: CLICKS_REPORT, createdBy: "agent" },
  { id: "rp_forecast", createdAt: ago(1 * DAY + 3 * HOUR), updatedAt: ago(1 * DAY + 3 * HOUR), siteId: SITE_ID, desk: "analytics", title: "Organic clicks forecast, next 8 weeks", html: FORECAST_REPORT, createdBy: "agent" },
  { id: "rp_queries", createdAt: ago(6 * DAY), updatedAt: ago(6 * DAY), siteId: SITE_ID, desk: "analytics", title: "Queries gaining impressions but losing clicks", html: QUERIES_REPORT, createdBy: "agent" },
  {
    id: "rp_seo_plan",
    createdAt: ago(4 * DAY + 6 * HOUR),
    updatedAt: ago(4 * DAY + 6 * HOUR),
    siteId: SITE_ID,
    desk: "seo",
    title: "Content plan: getting paid on time",
    html: reportHtmlFromAnswer(
      "Content plan: getting paid on time",
      [
        "Built 9 keyword clusters for getting paid on time, added 2 you already had, and kept 7 that fit.",
        "",
        "**Hub page (new):** /guides/getting-paid — targets *how to get clients to pay* (2,900/mo) and links every page below.",
        "",
        "**Pages to update**",
        "- /blog/invoice-payment-terms — add the *net 30 meaning* and *due on receipt* clusters; it already ranks 12.",
        "- /blog/late-fee-invoice — add the *late fee wording* cluster as its own section.",
        "",
        "**New pages**",
        "- Deposit invoice template — the transactional cluster no page covers (720/mo).",
        "- What to do when a client will not pay — the step after the reminder emails.",
        "",
        "Nothing is written; which pages to create is for the owner to decide.",
      ].join("\n"),
      "SEO desk · ledgerly.app",
      "keyword clusters built from DataForSEO keyword data, and the site's crawled pages",
    ),
    createdBy: "agent",
  },
  {
    id: "rp_tech_review",
    createdAt: ago(2 * DAY + 4 * HOUR),
    updatedAt: ago(2 * DAY + 4 * HOUR),
    siteId: SITE_ID,
    desk: "technical-seo",
    title: "Technical review: what is worth fixing first",
    html: reportHtmlFromAnswer(
      "Technical review: what is worth fixing first",
      [
        "Reviewed the open technical findings with the owner. Three are worth the time; the rest are cosmetic.",
        "",
        "| Finding | Pages | Why it matters |",
        "|---|---|---|",
        "| Orphan pages | 3 | /compare/bonsai gets no internal links, so Google has not crawled it. |",
        "| Duplicate titles | 6 | Help articles share one title, so search results cannot tell them apart. |",
        "| Redirect chains | 4 | Old /pricing URLs hop twice before landing. |",
        "",
        "Rejected as cosmetic: missing alt text on decorative icons, and two meta descriptions a few characters over length.",
      ].join("\n"),
      "Technical SEO desk · ledgerly.app",
      "the technical audit of the latest crawl",
    ),
    createdBy: "agent",
  },
];

type Turn = [role: "user" | "assistant", text: string];

interface ChatSeed {
  id: string;
  title: string;
  startedAgo: number;
  turns: Turn[];
}

const chartBlock = (html: string) => "```chart\n" + `<!doctype html><html><head><style>body{margin:0;padding:10px;font-family:system-ui,sans-serif;background:#fff}.chart svg{display:block;width:100%;height:auto}</style></head><body>${html}</body></html>` + "\n```";

const CHATS_SEED: ChatSeed[] = [
  {
    id: "ch_clicks",
    title: "Where did clicks change in the last 28 days, and which pages drove it?",
    startedAgo: 3 * DAY + 6 * HOUR,
    turns: [
      ["user", "Where did clicks change in the last 28 days, and which pages drove it?"],
      [
        "assistant",
        `I shaped ${SPAN} days of Search Console page × day rows into a workspace table and ran changepoint detection on daily clicks with the weekly pattern removed.\n\n**There is one clear changepoint on ${day(CHANGE_DAY)}.** Clicks moved from about **${fmt(BEFORE_AVG)}/day** to **${fmt(AFTER_AVG)}/day**, a ${Math.abs(CHANGE_PCT).toFixed(1)}% step down. It is flat on both sides, so this is a level shift, not a slow decline.\n\n${chartBlock(clicksChart(true))}\n\nThe drop is concentrated in a few pages:\n\n| Page | Clicks/day before | After | Position |\n|---|---:|---:|---|\n| /compare/quickbooks | 58 | 31 | 3.2 → 6.1 |\n| /compare/freshbooks | 34 | 22 | 4.0 → 5.8 |\n| /blog/quickbooks-alternatives | 27 | 16 | 5.1 → 8.3 |\n| /templates/invoice | 96 | 87 | 3.1 → 3.3 |\n| /tools/tax-estimator | 21 | 29 | 7.4 → 4.9 |\n\nThe three QuickBooks/FreshBooks comparison pages lost 2–3 positions on the same day and explain most of the lost clicks. The tax estimator gained and softened the fall.\n\nConfidence is **high**: 67 days before the change and 23 after, and the shift is far outside the normal weekly noise.`,
      ],
      ["user", "Is it a Google update or something we changed?"],
      [
        "assistant",
        `I can't see Google's side, but I can rule out the obvious things on yours:\n\n- **No crawl change.** The last two crawls show the same title, H1 and status for all three comparison pages, and none of them changed content hash around ${day(CHANGE_DAY)}.\n- **No indexing change.** All three stay indexed with the same canonical.\n- **Impressions held up** (−6%) while position fell. That is what it looks like when other results move above you, not when a page drops out.\n\nThree pages in the same topic moving on the same day, with nothing changed on the site, fits a ranking update better than anything on your side.\n\nOne thing worth checking yourself: /compare/quickbooks still shows QuickBooks pricing from March. If the pages now above it have this year's prices, that is the most likely gap. I have not changed anything.`,
      ],
      ["user", "Save this as a report"],
      ["assistant", `Saved as **Organic clicks changepoint, ${day(CHANGE_DAY)}** with the chart, the page table and the source tables. You'll find it under Reports.`],
    ],
  },
  {
    id: "ch_forecast",
    title: "Forecast organic clicks for the next 8 weeks.",
    startedAgo: 1 * DAY + 4 * HOUR,
    turns: [
      ["user", "Forecast organic clicks for the next 8 weeks."],
      [
        "assistant",
        `I rolled Search Console clicks up to weeks (${weeklyClicks.length} full weeks) and fitted a trend + weekly model, holding the last 4 weeks back to check it. Holdout error was **4.6%**, which is good for this amount of history.\n\n${chartBlock(forecastChart(true))}\n\n**Expected over the next 8 weeks: ${fmt(FORECAST_TOTAL)} clicks** (80% interval ${fmt(FORECAST_LO)}–${fmt(FORECAST_HI)}), about +1.2% a week.\n\nTwo caveats:\n\n1. The model starts from the level *after* the ${day(CHANGE_DAY)} drop. If the comparison pages win their positions back, expect the upper half of the band.\n2. Weeks 7 and 8 fall into the late-year dip. With only ${weeklyClicks.length} weeks of history the model can't learn a yearly pattern, so that dip is the least certain part.\n\nConfidence: **moderate**.`,
      ],
      ["user", "Save this as a report"],
      ["assistant", "Saved as **Organic clicks forecast, next 8 weeks**, with the week-by-week table and the interval."],
    ],
  },
  {
    id: "ch_queries",
    title: "Which queries gain impressions but lose clicks?",
    startedAgo: 6 * DAY + 2 * HOUR,
    turns: [
      ["user", "Which queries gain impressions but lose clicks?"],
      [
        "assistant",
        `I compared the last 28 days with the 28 before, per query and page, and kept queries with at least 5,000 impressions where impressions rose and clicks fell.\n\n| Query | Impressions | Clicks | CTR | Position |\n|---|---:|---:|---|---|\n${queriesTable.map((r) => `| ${r.q} | ${sign(r.di)} | ${sign(r.dc)} | ${r.ctr0.toFixed(1)}% → ${r.ctr1.toFixed(1)}% | ${r.pos[0]} → ${r.pos[1]} |`).join("\n")}\n\nPosition barely moved on any of them, so this is **not a ranking problem**. Four of the five are question or template queries where the results page now answers directly, and fewer clicks at the same position is the usual sign of that.\n\nIf you want to act on it, the cheapest test is the title on /templates/invoice: it says "Free invoice template" and nothing an answer box can't. A title that names the formats (PDF, Word, Google Docs) and a filled example might win some clicks back. That's a call for you; I'd try one page before touching the rest.`,
      ],
      ["user", "Save this as a report"],
      ["assistant", "Saved as **Queries gaining impressions but losing clicks**."],
    ],
  },
  {
    id: "ch_signups",
    title: "Which blog sections drive trial signups?",
    startedAgo: 9 * DAY + 5 * HOUR,
    turns: [
      ["user", "Which blog sections drive trial signups?"],
      [
        "assistant",
        `I joined 90 days of GA4 organic sessions and the \`trial_started\` key event to the site's page sections, crediting each signup to the landing page of the session it happened in.\n\n| Section | Organic sessions | Trial signups | Signups per 1k |\n|---|---:|---:|---:|\n${sectionsTable}\n\nThe blog itself is not where signups come from. The **comparison pages** convert at **22 per 1k sessions**, almost 3× the templates and 8.5× the tax posts. Templates bring the most signups in total (302) only because they bring the most visits.`,
      ],
      ["user", "Is that just because comparison readers are further along? Does the tax blog help later?"],
      [
        "assistant",
        `Partly, yes. I checked returning visitors: of the 747 signups, **118 had an earlier session that landed on a tax post** within 30 days. So first-touch attribution undercounts the tax blog.\n\nEven if every one of those 118 is credited to the tax blog instead, it rises to about **6.8 per 1k**, still well below comparisons and templates. The order does not change.\n\nConfidence is **moderate**: GA4 only links sessions for visitors who keep the same cookie, so cross-device journeys are missing.`,
      ],
      ["user", "Save this as a report"],
      ["assistant", "Saved as **Which site sections drive trial signups**, with the section table, the chart and a note on attribution."],
    ],
  },
  {
    id: "ch_templates",
    title: "Do template downloads lead to more signups than blog reads?",
    startedAgo: 13 * DAY,
    turns: [
      ["user", "Do people who download a template sign up more than people who just read a blog post?"],
      [
        "assistant",
        `Yes, clearly. Over the last 90 days of organic sessions:\n\n| Visitor did | Sessions | Signed up within 14 days | Rate |\n|---|---:|---:|---:|\n| Downloaded a template | 9,840 | 271 | 2.75% |\n| Read a blog post, no download | 58,200 | 204 | 0.35% |\n\nI ran a causal-effect estimate controlling for landing section, device and country, so it isn't just that template pages attract a different crowd. The estimated lift from a download is **+1.9 percentage points** (95% CI 1.5–2.3).\n\nConfidence: **moderate**. Downloads are self-selected, and the controls can't capture intent fully.`,
      ],
      ["user", "Which template converts best?"],
      [
        "assistant",
        `| Template | Downloads | Signups | Rate |\n|---|---:|---:|---:|\n| Profit and loss | 610 | 31 | 5.1% |\n| Invoice | 5,420 | 152 | 2.8% |\n| Quote | 1,180 | 33 | 2.8% |\n| Expense report | 840 | 19 | 2.3% |\n| Cash flow | 1,020 | 21 | 2.1% |\n| Receipt | 770 | 15 | 1.9% |\n\nThe profit and loss template converts best but gets the fewest downloads. It has two internal links pointing at it, against 40 for the invoice template. More links to it would be a reasonable experiment; I haven't changed anything.`,
      ],
    ],
  },
  {
    id: "ch_mobile",
    title: "Why is mobile conversion lower on the pricing page?",
    startedAgo: 17 * DAY,
    turns: [
      ["user", "Why is mobile conversion lower on the pricing page?"],
      [
        "assistant",
        `On /pricing over 90 days, desktop sessions start a trial at **6.4%** and mobile at **2.1%**. Mobile is 44% of the page's traffic, so the gap matters.\n\nWhat the data shows:\n\n- **Engagement drops before the plan table.** Mobile sessions average 18 s on the page against 52 s on desktop, and 61% of mobile sessions never scroll past the first screen.\n- **The last crawl flags the mobile render.** The plan table is 1,240 px wide on a 390 px viewport, so it scrolls sideways.\n- **It isn't traffic quality.** Mobile visitors who reach /pricing from /compare convert at 5.8% on desktop and 2.3% on mobile, the same gap.\n\nThe sideways-scrolling table is the most likely cause. Stacking the three plans on mobile is worth testing; whether to do it is your call.`,
      ],
    ],
  },
];

export const CHATS: AnalyticsChat[] = [];
export const MESSAGES: Record<string, AnalyticsChatMessage[]> = {};

for (const seed of CHATS_SEED) {
  const step = 4 * 60_000;
  const messages = seed.turns.map(([role, text], i) => ({
    id: `msg_${seed.id}_${i + 1}`,
    role,
    text,
    createdAt: new Date(NOW - seed.startedAgo + i * step).toISOString(),
  }));
  MESSAGES[seed.id] = messages;
  CHATS.push({
    id: seed.id,
    siteId: SITE_ID,
    title: seed.title,
    sdkSessionId: `sdk_${seed.id}`,
    createdAt: messages[0].createdAt,
    updatedAt: messages[messages.length - 1].createdAt,
  });
}

export function reportHtmlFromAnswer(title: string, markdown: string, meta = "Analytics chat · ledgerly.app", source = "the site's Search Console and Analytics tables in the analytics workspace"): string {
  const blocks = markdown
    .replace(/```chart\n([\s\S]*?)\n```/g, (_m, html: string) => {
      const body = html.match(/<body>([\s\S]*)<\/body>/);
      return `\u0000${body ? body[1] : ""}\u0000`;
    })
    .split(/\n{2,}/);
  const inline = (s: string) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
  const html = blocks
    .map((block) => {
      const raw = block.trim();
      if (!raw) return "";
      if (raw.startsWith("\u0000")) return raw.replace(/\u0000/g, "");
      const lines = raw.split("\n");
      if (lines.length >= 2 && lines[0].startsWith("|") && /^\|[-:| ]+\|$/.test(lines[1])) {
        const cells = (l: string) => l.replace(/^\||\|$/g, "").split("|").map((c) => inline(c.trim()));
        const head = cells(lines[0]).map((c) => `<th>${c}</th>`).join("");
        const rows = lines.slice(2).map((l) => `<tr>${cells(l).map((c) => `<td>${c}</td>`).join("")}</tr>`).join("");
        return `<table><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
      }
      if (lines.every((l) => /^(-|\d+\.)\s/.test(l))) {
        return `<ul>${lines.map((l) => `<li>${inline(l.replace(/^(-|\d+\.)\s/, ""))}</li>`).join("")}</ul>`;
      }
      return `<p>${inline(raw.replace(/\n/g, " "))}</p>`;
    })
    .join("\n");
  return page(title, meta, `${html}<div class="source">Source: ${esc(source)}.</div>`);
}
