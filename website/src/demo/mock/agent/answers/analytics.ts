import { lastAnalyticsAnswer, saveAnalyticsReport } from "../hooks";
import { PAGES } from "../../data/site";
import { chartBars, chartLine, fence, lines, link, text, tool, type Ctx, type Script } from "./common";

function weeks(n: number): string[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(Date.now() - (n - 1 - i) * 7 * 86_400_000);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  });
}

function clicksChanged(): string {
  return lines(
    "I built a workspace table of daily page clicks for the last 56 days from Search Console (`gsc_page_daily_56d`, 7,412 rows) and compared the last 28 days with the 28 before.",
    "",
    "**Clicks 2,208 → 2,671 (+21%).** The comparison is significant (Mann–Whitney on daily totals, p < 0.01) — high trust, 28 days a side.",
    "",
    fence("chart", chartBars("Click change by page, last 28 vs previous 28 days", [["/templates/invoice", 214], ["/blog/quarterly-estimated…", 168], ["/compare/quickbooks", 72], ["/tools/tax-estimator", 41], ["/blog/wave-shutting-down…", -38], ["/blog/best-bookkeeping…", -91]])),
    "",
    `- ${link("/templates/invoice")} carries 46% of the gain — a position move (5.8 → 4.1), not more demand.`,
    `- ${link("/blog/quarterly-estimated-taxes-explained")} is seasonal: the September 15 deadline. Expect it back down in October.`,
    `- ${link("/blog/best-bookkeeping-software-freelancers")} is the one real loss: position flat, click-through 3.4% → 2.3%.`,
    "",
    "Caveat: two days of Search Console data are still provisional, so the last two bars may move by a few clicks.",
  );
}

function impressionsNotClicks(): string {
  return lines(
    "From `gsc_query_daily_56d` (queries with at least 100 impressions in both windows, 312 queries):",
    "",
    "| Query | Impr. Δ | Clicks Δ | Position | Likely reason |",
    "|---|---|---|---|---|",
    "| best bookkeeping software | +1,840 | −41 | 7.1 | A dated title against fresher results |",
    "| invoice template free | +3,210 | −12 | 4.6 | An AI overview now answers above the results |",
    "| wave accounting free | +960 | −22 | 9.8 | Navigational — people want Wave itself |",
    "| freelance tax calculator | +720 | −9 | 10.4 | Position slipped a place, off the fold |",
    "",
    "Only the first is yours to fix with a page edit. The second is the results page changing shape, and the third is not your traffic to win. Trust: moderate — click deltas under 50 on single queries are noisy.",
  );
}

function forecast(): string {
  const past = [412, 438, 451, 470, 462, 489, 503, 521, 548, 566, 572, 601];
  const ahead = [618, 630, 641, 655, 662, 676, 688, 701];
  const labels = weeks(20);
  return lines(
    "Forecast of weekly organic clicks from 16 months of Search Console history (seasonal model, weekly seasonality, holdout error 6.8%).",
    "",
    fence(
      "chart",
      chartLine(
        "Weekly organic clicks — actual and forecast",
        [
          { name: "Actual", color: "#0f766e", points: past },
          { name: "Forecast", color: "#6366f1", dashed: true, start: past.length - 1, points: [past[past.length - 1], ...ahead] },
        ],
        labels,
      ),
    ),
    "",
    "- **Next 8 weeks: ~5,270 clicks** (80% range 4,810–5,730), about 660 a week by mid-December.",
    "- The trend is driven by the invoice template; take it away and the rest of the site is flat.",
    "- The model sees last year's December dip, so the curve flattens in the last two weeks.",
    "",
    "Trust: moderate. A forecast assumes nothing changes — a core update or a new page would break it.",
  );
}

function converts(): string {
  return lines(
    "Joined GA4 landing pages (organic only) with `sign_up` key events, last 28 days:",
    "",
    fence("chart", chartBars("Organic sign-up rate by landing page (%)", [["/pricing", 5.9], ["/compare/freshbooks", 5.1], ["/compare/quickbooks", 4.7], ["/", 3.2], ["/templates/invoice", 0.5], ["/blog/quarterly-estimated…", 0.3]])),
    "",
    `- **Best:** ${link("/pricing")} and the comparison pages — people who arrive deciding.`,
    `- **Most traffic, least conversion:** ${link("/templates/invoice")} (1,880 sessions, 9 sign-ups).`,
    "",
    "The comparison pages convert ten times better than the template but get a third of the traffic. That is the clearest lever in the data; what to do with it is your call.",
  );
}

function generic(ctx: Ctx): string {
  return lines(
    "I profiled the tables this desk can read for ledgerly.app before answering:",
    "",
    "- `site_search_daily` — 16 months of Search Console by page and query",
    "- `site_traffic_daily` — 16 months of GA4 sessions and key events",
    `- \`site_pages\` — ${PAGES.length} crawled pages with type, depth and links`,
    "",
    `To answer "${ctx.message.slice(0, 120)}" properly I would shape those into one workspace table and run the matching analysis — period comparison, drivers, clusters or a forecast. Tell me the time window and the metric you care about and I will run it — or try "where did clicks change", "forecast organic clicks" or "which pages convert".`,
  );
}

const SAVE_PROMPT = "save your last answer as a report";

function titleFor(answer: string): string {
  if (/forecast/i.test(answer)) return "Organic clicks forecast — next 8 weeks";
  if (/impressions.*clicks|Impr\. Δ/i.test(answer)) return "Queries gaining impressions but losing clicks";
  if (/sign-up/i.test(answer)) return "Which organic landing pages convert";
  if (/Clicks 2,208/.test(answer)) return "What changed in clicks, last 28 days";
  return "Analysis — " + new Date().toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function analyticsAnswer(ctx: Ctx): Script {
  const l = ctx.lower;
  if (l.includes(SAVE_PROMPT)) {
    const answer = ctx.memory.lastAnswer || lastAnalyticsAnswer(ctx.sessionId) || "";
    if (!answer.trim()) return [text("There is no answer in this chat to save yet. Ask a question first, then save it.")];
    const title = titleFor(answer);
    return [
      {
        kind: "write",
        tool: "analytics_save_report",
        input: { title },
        apply: () => {
          saveAnalyticsReport(title, answer);
        },
        after: `Saved as **${title}** — it is under Reports on the Analytics desk, with the numbers, the charts and where the data came from.`,
        declined: "Not saved. The answer stays in this chat.",
      },
    ];
  }
  if (/where did clicks change|clicks? (change|drop|fell|fall|rose|grew)|what changed|changepoint/.test(l)) return [tool("run_sql"), tool("compare_periods"), tool("explain_metric"), text(clicksChanged())];
  if (/impressions?/.test(l)) return [tool("run_sql"), tool("compare_periods"), text(impressionsNotClicks())];
  if (/forecast|predict|next \d+ (weeks|months)|projection/.test(l)) return [tool("run_sql"), tool("profile"), tool("forecast"), text(forecast())];
  if (/convert|sign.?ups?|trials?|leads?/.test(l)) return [tool("run_sql"), tool("group_aggregate"), text(converts())];
  return [tool("run_sql"), tool("profile"), text(generic(ctx))];
}
