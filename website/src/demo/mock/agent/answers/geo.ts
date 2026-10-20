import type { GeoQuery } from "@demo/lib/types";
import { call } from "../hooks";
import { isYes, lines, link, text, tool, type Ctx, type Script, type Step } from "./common";

const SUGGESTED = [
  "How much should a freelance designer charge per hour in 2026?",
  "What should a freelance invoice include to get paid on time?",
  "Do I need an accountant if I use bookkeeping software?",
  "How do I track business mileage for taxes?",
  "What is the difference between a quote and an invoice?",
];

function queries(): GeoQuery[] {
  return call<GeoQuery[]>("GET", "/api/v1/geo/queries") ?? [];
}

function saveStep(texts: string[]): Step {
  return {
    kind: "write",
    tool: "geo_save_queries",
    input: { questions: texts },
    apply: () => {
      call("POST", "/api/v1/geo/queries", texts.map((t) => ({ text: t, source: "suggested" })));
    },
    after: `Saved ${texts.length} questions on the GEO desk. Press **Check now** to see whether a page answers each one and what ChatGPT, Claude and AI Overviews cite.`,
    declined: "Nothing saved. Tell me which ones to keep or how to reword them.",
  };
}

export function geoSetup(ctx: Ctx): Script {
  const tracked = new Set(queries().map((q) => q.text));
  const fresh = SUGGESTED.filter((t) => !tracked.has(t));
  ctx.memory.pending = () => [saveStep(fresh)];
  return [
    tool("run_sql"),
    tool("add_desk"),
    tool("search_suggestions"),
    tool("people_also_ask"),
    text(
      lines(
        `I read the site record, the profile and the ${tracked.size} questions already tracked, then checked what people search before they reach ledgerly.app and what Google lists under People also ask.`,
        "",
        "Questions worth tracking, each one a freelancer would type into ChatGPT before choosing a tool:",
        "",
        ...fresh.map((t, i) => `${i + 1}. ${t}`),
        "",
        "Rates and mileage come from Search Console queries that already bring clicks; the other three are People-also-ask questions on keywords you rank for.",
        "",
        "Say **yes** to save them, or tell me which to drop or reword.",
      ),
    ),
  ];
}

export function askGeo(ctx: Ctx): Script {
  const l = ctx.lower;
  const rows = queries();
  const done = rows.filter((q) => q.latestCheck?.status === "done");
  if (/related|more questions|worth tracking|suggest/.test(l)) return geoSetup(ctx);
  const gaps = done.filter((q) => q.latestCheck?.verdict === "no_page" || q.latestCheck?.verdict === "partial");
  const cited = done.filter((q) => q.latestCheck?.aiAnswers.some((a) => a.citedUs));
  const lowRank = done.filter((q) => q.latestCheck?.verdict === "low_rank");
  return [
    tool("run_sql"),
    tool("run_sql"),
    text(
      lines(
        `${done.length} of ${rows.length} questions have a finished check. ${cited.length} are cited by at least one AI answer.`,
        "",
        "**Where the site has a gap**",
        ...gaps.map((q) => {
          const c = q.latestCheck!;
          const missing = c.aiAnswers.flatMap((a) => a.covers).filter((p, i, all) => all.indexOf(p) === i).slice(0, 2);
          return `- *${q.text}* — ${c.verdict === "no_page" ? "no page answers it" : `${c.pageUrl ? link(new URL(c.pageUrl).pathname) : "a page"} comes close`}. AI answers lead with ${missing.join(" and ").toLowerCase() || "points the page skips"}.`;
        }),
        "",
        lowRank.length ? "**Answered, but ranked too low to be found**" : "",
        ...lowRank.map((q) => `- *${q.text}* — the page answers every point but sits around position ${q.latestCheck?.position?.toFixed(0)}. That is a ranking problem for the SEO desk, not a writing one.`),
        "",
        "These are suggestions. Whether to extend a page, write a new one or leave it is your call; open a question on the GEO screen to see the evidence behind each.",
      ),
    ),
  ];
}

export function geoAnswer(ctx: Ctx): Script {
  if (ctx.action === "geo-setup") return geoSetup(ctx);
  if (isYes(ctx.lower)) return [text("Tell me which questions you want saved and I will add them.")];
  return askGeo(ctx);
}
