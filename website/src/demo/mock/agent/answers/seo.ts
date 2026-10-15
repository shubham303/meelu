import { addKeywordClusters, call, trackKeywords } from "../hooks";
import { cap, chartBars, chartLine, fence, lines, link, quoted, text, tool, topicFrom, type Ctx, type Script, type Step } from "./common";

function listWrite(list: "competitors" | "backlink_opportunities", verb: "add" | "remove", items: string[], after: string): Step {
  return {
    kind: "write",
    tool: verb === "add" ? "add_to_seo_list" : "remove_from_seo_list",
    input: { list, items },
    apply: () => {
      call("POST", `/api/v1/site/seo/${list}/${verb}`, { items });
    },
    after,
    declined: "Fine — the list is unchanged.",
  };
}

function changed(): Script {
  return [
    tool("run_sql"),
    tool("compare_periods"),
    tool("search_page"),
    text(
      lines(
        "Last 90 days against the 90 before, from Search Console. Clicks 4,812 → 5,930 (+23%), impressions 212k → 268k, average position 18.4 → 16.9. Enough volume for the page-level movements below to mean something.",
        "",
        fence("chart", chartBars("Click change by page, last 90 days", [["/templates/invoice", 412], ["/blog/quarterly-estimated…", 288], ["/compare/quickbooks", 141], ["/tools/tax-estimator", 96], ["/blog/wave-shutting-down…", -118], ["/blog/best-bookkeeping…", -164]])),
        "",
        "**Gained**",
        `- ${link("/templates/invoice")} +412 clicks — 'free invoice template' moved 7.2 → 4.1.`,
        `- ${link("/blog/quarterly-estimated-taxes-explained")} +288 — seasonal; the September 15 deadline. Expect it to fall back in October.`,
        `- ${link("/compare/quickbooks")} +141 — 'quickbooks alternative' 14.8 → 11.3.`,
        "",
        "**Lost**",
        `- ${link("/blog/best-bookkeeping-software-freelancers")} −164. Position held (6.8 → 7.1) but click-through halved. The title still says \"in 2025\" — the likeliest reason, since searchers skip a dated list.`,
        `- ${link("/blog/wave-shutting-down-features")} −118. The news is a year old; the query volume itself dropped 60%. Nothing to fix.`,
        "",
        "Only the first loser looks fixable, and it is a one-line title change you can make yourself.",
      ),
    ),
  ];
}

function striking(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "Queries where Ledgerly already ranks 8–15 with real impressions (last 28 days):",
        "",
        "| Query | Pos. | Impr. | Page | Inlinks | Needs |",
        "|---|---|---|---|---|---|",
        `| quickbooks alternative | 11.3 | 6,210 | ${link("/compare/quickbooks")} | 4 | **Links** |`,
        `| invoice payment terms | 11.4 | 3,870 | ${link("/blog/invoice-payment-terms")} | 2 | **Links** |`,
        `| self employed tax calculator | 9.6 | 2,940 | ${link("/tools/tax-estimator")} | 11 | **Content** |`,
        `| late fee on invoice | 12.8 | 1,620 | ${link("/blog/late-fee-invoice")} | 3 | **Links** |`,
        `| freshbooks alternative | 8.9 | 1,410 | ${link("/compare/freshbooks")} | 9 | **Content** |`,
        "",
        "The two with almost no inlinks are the cheap wins — the Structure desk's \"Send authority to money pages\" strategy would find sources for both. The tax calculator is already well linked; it ranks 9.6 because the page around the tool is 420 words against competitors' 1,500, so it needs content, not links.",
      ),
    ),
  ];
}

function invisible(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "From the index status record (checked 3 days ago):",
        "",
        "- **Indexed:** 146 pages.",
        `- **Discovered, not crawled:** 3 — ${link("/compare/bonsai")}, ${link("/dpa")}, ${link("/webinars/pricing-your-work")}. All three are orphans; Google knows the URL from the sitemap but nothing on the site points at them, so it does not bother.`,
        "- **Crawled, not indexed:** 11 — mostly short help-centre articles and two tax-season recap posts. That is Google reading the page and declining it. It rules out a technical block; it is a content verdict.",
        "- **Excluded:** 4 noindex pages (tag archives, /press) — intentional.",
        "",
        "The bucket worth acting on is the orphans: link /compare/bonsai from the other comparison pages and it will most likely be crawled within a week. The 11 declined pages need merging or more substance, not resubmission.",
      ),
    ),
  ];
}

function dropFollowUp(ctx: Ctx): Script {
  const path = (ctx.message.match(/\/[a-z0-9\-/]+/i)?.[0] ?? "/blog/best-bookkeeping-software-freelancers").replace(/\/$/, "");
  return [
    tool("run_sql"),
    tool("search_page"),
    text(
      lines(
        `**${path}**, last 28 days against the 28 before:`,
        "",
        "- Clicks 612 → 401 (−34%). Impressions 18.2k → 17.6k (−3%).",
        "- Position 6.8 → 7.1 — essentially unchanged.",
        "- Click-through 3.4% → 2.3%.",
        "- Index: still indexed, last crawled 4 days ago, canonical as declared.",
        "",
        "So the page did not drop in ranking; fewer people click it. The data can support that much. It cannot tell me why — but the title still names last year, and the two results above it now say 2026. That is the likeliest cause; a title edit would test it within two weeks.",
      ),
    ),
  ];
}

function traffic(l: string): Script {
  if (l.includes("where sessions actually come from")) {
    return [
      tool("run_sql"),
      tool("compare_periods"),
      text(
        lines(
          "Last 28 days of Google Analytics, 9,840 sessions:",
          "",
          fence("chart", chartBars("Sessions by channel, last 28 days", [["Organic Search", 5212], ["Direct", 2104], ["Referral", 1188], ["Organic Social", 702], ["Email", 448], ["Paid Search", 186]])),
          "",
          "- **Organic Search carries the site** — 53% of sessions, up from 49%.",
          "- **Referral** grew 31%, almost all from one accountant directory linking /partners/accountants. Real, but one source.",
          "- **Organic Social** +18% is 108 sessions; at this volume that is one Reddit thread, not a trend.",
          "- **Paid Search** fell to 186 — that matches the campaign pause, not a problem.",
        ),
      ),
    ];
  }
  if (l.includes("produce key events")) {
    return [
      tool("run_sql"),
      tool("group_aggregate"),
      text(
        lines(
          "Key event here is `sign_up`. Last 28 days, by landing page:",
          "",
          "| Landing page | Sessions | Sign-ups | Rate |",
          "|---|---|---|---|",
          `| ${link("/pricing")} | 1,040 | 61 | 5.9% |`,
          `| ${link("/compare/quickbooks")} | 612 | 29 | 4.7% |`,
          `| ${link("/")} | 2,310 | 74 | 3.2% |`,
          `| ${link("/templates/invoice")} | 1,880 | 9 | 0.5% |`,
          `| ${link("/blog/quarterly-estimated-taxes-explained")} | 1,120 | 3 | 0.3% |`,
          "",
          "- **Traffic that converts nothing:** the invoice template and the tax post bring 3,000 sessions and 12 sign-ups between them. They do their job as top-of-funnel pages; neither has a product mention above the fold.",
          "- **Converts well, gets little:** the comparison pages. /compare/freshbooks converts at 5.1% on 230 sessions.",
          "",
          "If you want more sign-ups from what you have, the comparison pages are where extra traffic is worth the most.",
        ),
      ),
    ];
  }
  if (l.includes("compare this period's traffic")) {
    return [
      tool("run_sql"),
      tool("compare_periods"),
      tool("detect_changepoints"),
      text(
        lines(
          "Sessions 8,610 → 9,840 (+14%) against the previous 28 days.",
          "",
          "- **Organic Search +920** — spread across 40+ landing pages, led by /templates/invoice. A real shift: the change point is September 22 and it has held for three weeks.",
          "- **Referral +280** — one source, an accountants' directory. Real, but fragile.",
          "- **Direct −110** — within normal week-to-week noise.",
          "- **One spike to ignore:** October 3 had 1,240 sessions, triple a normal day, from a Hacker News comment linking /blog/how-we-price-ledgerly. It is in the total but not in the trend.",
          "",
          "By country, the US carried 81% of the gain; the UK and Canada are flat.",
        ),
      ),
    ];
  }
  return [
    tool("run_sql"),
    tool("compare_periods"),
    text(
      lines(
        "Organic Search is 53% of sessions (5,212 of 9,840), up from 49% the period before.",
        "",
        "Engagement, organic vs everything else: 61% engaged sessions vs 54%, 1m 48s average vs 1m 21s. Organic visitors read more, which fits a site whose traffic comes from how-to posts.",
        "",
        "Cross-checking Search Console: clicks rose 18% in the same window while average position improved 1.5 places, so the growth is ranking, not just seasonal demand. Organic is pulling its weight; the weak spot is that it converts at 1.1% against 5.9% for visitors who land on /pricing directly.",
      ),
    ),
  ];
}

function targetNext(): Script {
  return [
    tool("run_sql"),
    {
      kind: "write",
      tool: "compute_metrics_for_cluster",
      input: { clusters: 6 },
      apply: () => {},
      after: "",
      declined: "Understood — I will rank only the clusters that already have a score.",
    },
    tool("seo_ranked_keywords"),
    text(
      lines(
        "I scored the 6 unscored clusters (most searched first) and ranked all 23 by winnability, then volume. The best five:",
        "",
        "| Cluster (main keyword) | Searches/mo | Winnable | Page that wins it |",
        "|---|---|---|---|",
        "| invoice payment terms | 4,400 | 78 | A guide — **/blog/invoice-payment-terms could own it** with a rewrite |",
        "| freelance tax deductions | 9,900 | 71 | A long list post — /blog/deductible-expenses-freelancers is close |",
        "| how to invoice as a freelancer | 3,600 | 69 | Step-by-step how-to — already yours at 6.2 |",
        "| quickbooks import | 1,300 | 66 | A help-style page — **new** |",
        "| 1099 contractor payments | 2,900 | 61 | A guide for people who *send* 1099s — **new** |",
        "",
        "Why these are winnable: the results above position 5 for each have weaker link profiles than Ledgerly's domain, and two are forum threads, which usually means search engines have nothing better.",
        "",
        "What the score cannot see is quality. I would start with the payment-terms page since it already exists — you decide whether to rewrite it or brief a new one on the Content desk.",
      ),
    ),
  ];
}

function clusterWrite(source: string, topic: string | null, summary: string): Step {
  return {
    kind: "write",
    tool: "create_keyword_clusters",
    input: topic ? { source, seeds: topic } : { source },
    apply: () => {
      addKeywordClusters(source, topic);
    },
    after: summary,
    declined: "Not built — no vendor credit spent.",
  };
}

function buildClustersFollowUp(ctx: Ctx): Script {
  const topic = topicFrom(ctx.message).toLowerCase();
  const seeds = [`${topic}`, `${topic} for freelancers`, `${topic} software`, `how to ${topic}`, `${topic} template`];
  ctx.memory.pending = () => [
    clusterWrite(
      "seeds",
      topic,
      lines(
        `Built from ${seeds.length} seeds: 1,240 keywords came back, 312 dropped as noise or off-topic, and 18 clusters came out.`,
        "",
        `Biggest by monthly searches: **${topic}** (8,100), **${topic} for freelancers** (2,400), **best ${topic} app** (1,900).`,
        "",
        "They are on the SEO screen with a winnability score each. Pick the ones worth a page — I have not planned any.",
      ),
    ),
  ];
  return [
    tool("search_page"),
    text(
      lines(
        `Seeds for **${topic}**, chosen from what Ledgerly sells:`,
        "",
        ...seeds.map((s) => `- ${s}`),
        "",
        "Building clusters spends vendor credit (about $0.40 for this many). Say **yes** to build them, or edit the list.",
      ),
    ),
  ];
}

interface SavedLists {
  competitors: string[];
  backlinkOpportunities: string[];
}

function saved(): SavedLists {
  const lists = call<SavedLists>("GET", "/api/v1/site/seo");
  return { competitors: lists?.competitors ?? [], backlinkOpportunities: lists?.backlinkOpportunities ?? [] };
}

const bare = (d: string) => d.replace(/^www\./, "").toLowerCase();

const COMPETITOR_CANDIDATES: Array<[string, number, string]> = [
  ["freshbooks.com", 1840, "Invoicing-first bookkeeping for freelancers. Direct."],
  ["waveapps.com", 1410, "Free bookkeeping for very small businesses; same templates intent."],
  ["hellobonsai.com", 930, "Freelancer suite with invoicing and tax estimates."],
  ["xero.com", 2120, "Broader, but competes on every 'small business bookkeeping' query."],
  ["freeagent.com", 760, "Bookkeeping and tax for freelancers; strong on the same how-to queries."],
  ["honeybook.com", 540, "Client management with invoicing; overlaps on contracts and payments."],
  ["invoiceninja.com", 480, "Invoice generator and templates — same top-of-funnel."],
];

function table(rows: Array<[string, number, string]>): string[] {
  return ["| Domain | Shared keywords | Why it counts |", "|---|---|---|", ...rows.map(([d, n, why]) => `| ${d} | ${n.toLocaleString("en-US")} | ${why} |`)];
}

function findCompetitors(ctx: Ctx): Script {
  const have = new Set(saved().competitors.map(bare));
  const fresh = COMPETITOR_CANDIDATES.filter(([d]) => !have.has(d));
  const already = COMPETITOR_CANDIDATES.filter(([d]) => have.has(d));
  const steps: Step[] = [tool("find_competitors"), tool("seo_ranked_keywords")];
  const intro = [
    "Domains that chase the same searchers for the same thing, across the US market:",
    "",
    ...table(COMPETITOR_CANDIDATES),
    "",
    "Left out: nerdwallet.com, forbes.com/advisor (review sites), reddit.com, irs.gov — they share keywords with everyone.",
    "",
  ];
  if (fresh.length === 0) return [...steps, text(lines(...intro, "All of them are already saved, so there is nothing to add."))];
  const keep = fresh.map(([d]) => d);
  ctx.memory.pending = () => [listWrite("competitors", "add", keep, `Saved ${keep.join(", ")}. Backlink opportunities and keyword gaps now compare against them too.`)];
  return [
    ...steps,
    text(
      lines(
        ...intro,
        already.length ? `${already.map(([d]) => d).join(", ")} ${already.length === 1 ? "is" : "are"} already saved.` : "",
        `Say **yes** to save ${keep.length === 1 ? keep[0] : `the ${keep.length} new ones (${keep.join(", ")})`}, or tell me which to drop.`,
      ),
    ),
  ];
}

const BACKLINK_CANDIDATES: Array<[string, string, string]> = [
  ["freelancersunion.org", "4 of 5", "Resource page: 'tools for getting paid'"],
  ["creativeboom.com", "3 of 5", "'Best invoicing apps for creatives' roundup"],
  ["smallbiztrends.com", "3 of 5", "Reviews of each tool"],
  ["aiga.org", "2 of 5", "Design business resources page"],
  ["contentfolks.com", "2 of 5", "Freelance writers' toolkit"],
  ["accountingtoday.com", "2 of 5", "News on Wave's free-tier changes"],
];

function findBacklinks(ctx: Ctx): Script {
  const have = new Set(saved().backlinkOpportunities.map(bare));
  const fresh = BACKLINK_CANDIDATES.filter(([d]) => !have.has(d)).map(([d]) => d);
  const steps: Step[] = [tool("find_backlink_opportunities")];
  const body = [
    "Sites linking to two or more of your saved competitors but not to ledgerly.app, most competitors linked first:",
    "",
    "| Site | Links to | What they link to |",
    "|---|---|---|",
    ...BACKLINK_CANDIDATES.map(([d, n, what]) => `| ${d}${have.has(d) ? " *(saved)*" : ""} | ${n} | ${what} |`),
    "",
    "Skipped 41 directories and link farms that link everything, plus the competitors themselves.",
    "",
  ];
  if (fresh.length === 0) return [...steps, text(lines(...body, "Every one of them is already on your list."))];
  ctx.memory.pending = () => [listWrite("backlink_opportunities", "add", fresh, `Saved ${fresh.join(", ")} to backlink opportunities. Reaching out is yours to do — I only keep the list.`)];
  return [...steps, text(lines(...body, `Say **yes** to save the ${fresh.length} not on your list yet.`))];
}

const NOT_COMPETITORS: Record<string, string> = {
  "bench.co": "sells a bookkeeper, not software — a different buyer making a different decision",
  "nerdwallet.com": "reviews every tool; it shares keywords, not customers",
  "indy.fyi": "a French-market tool; it shares English keywords only through its blog",
  "invoicesimple.com": "an invoice app with no bookkeeping — it overlaps on templates only",
};

const NOT_WORTH_ASKING: Record<string, string> = {
  "solopreneurhub.io": "a link directory that lists anything that pays",
  "paymentsjournal.com": "payments-industry news; it would not link a bookkeeping tool",
  "doola.com": "sells company formation and its own bookkeeping — a competitor, not a linker",
};

function cleanCompetitors(ctx: Ctx): Script {
  const list = saved().competitors;
  const flagged = list.filter((d) => NOT_COMPETITORS[bare(d)]);
  const steps: Step[] = [tool("run_sql"), tool("find_competitors")];
  if (flagged.length === 0) return [...steps, text(`All ${list.length} saved competitors sell what you sell to the same buyer. Nothing to remove.`)];
  ctx.memory.pending = () => [listWrite("competitors", "remove", flagged, `Removed ${flagged.join(", ")} from competitors.`)];
  return [
    ...steps,
    text(
      lines(
        `Of the ${list.length} saved competitors, ${flagged.length === 1 ? "one does" : `${flagged.length} do`} not belong:`,
        "",
        ...flagged.map((d) => `- **${d}** — ${NOT_COMPETITORS[bare(d)]}.`),
        "",
        "The others chase the same searchers for the same thing. Say **yes** to remove the flagged ones.",
      ),
    ),
  ];
}

function rankBacklinks(ctx: Ctx): Script {
  const list = saved().backlinkOpportunities;
  const flagged = list.filter((d) => NOT_WORTH_ASKING[bare(d)]);
  const good = list.filter((d) => !NOT_WORTH_ASKING[bare(d)]).slice(0, 5);
  if (flagged.length) ctx.memory.pending = () => [listWrite("backlink_opportunities", "remove", flagged, `Removed ${flagged.join(", ")}.`)];
  return [
    tool("run_sql"),
    text(
      lines(
        `Ranked the ${list.length} saved sites by how plausible a link to Ledgerly is. The top of the list:`,
        "",
        ...good.map((d, i) => `${i + 1}. **${d}**`),
        "",
        flagged.length
          ? lines("Not worth asking:", ...flagged.map((d) => `- **${d}** — ${NOT_WORTH_ASKING[bare(d)]}.`), "", "Say **yes** to remove those.")
          : "Nothing on the list looks like spam.",
      ),
    ),
  ];
}

function clusterChip(ctx: Ctx): Script | null {
  const l = ctx.lower;
  const kw = quoted(ctx.message) ?? "this cluster";
  if (l.includes("plan one page that targets")) {
    return [
      tool("seo_relevant_pages"),
      tool("search_page"),
      text(
        lines(
          `**Brief: ${kw}**`,
          "",
          `- **Title:** ${cap(kw)}: a plain guide for freelancers`,
          `- **H1:** ${cap(kw)}, explained`,
          `- **Meta description:** What ${kw} means, which option suits a one-person business, and the wording to use — with a free template.`,
          "",
          "**Outline**",
          "1. The short answer (two sentences)",
          "2. The options, side by side",
          "3. Which one to pick, by situation",
          "4. Wording you can copy",
          "5. What to do when it goes wrong",
          "",
          `**Other keywords to answer:** ${kw} examples, ${kw} for small business, ${kw} template.`,
          "",
          "**Weakest results above you:** position 3 is a 2019 forum thread; position 5 is a bank's product page with 200 words on the topic. A complete page with a template beats both.",
          "",
          "If you want it written, take this brief to the Content desk.",
        ),
      ),
    ];
  }
  if (l.includes("explain the winnability score")) {
    return [
      tool("seo_relevant_pages"),
      text(
        lines(
          `Winnability for **${kw}**, result by result above you:`,
          "",
          "| # | Result | Their link strength vs yours | Serves the search? | Chance to pass |",
          "|---|---|---|---|---|",
          "| 1 | freshbooks.com guide | Much stronger | Yes | Low |",
          "| 2 | investopedia.com | Much stronger | Partly — a definition | Low |",
          "| 3 | reddit.com thread | Weaker | Partly | **High** |",
          "| 4 | smallbizhub blog | Weaker | Yes, but 2021 | **High** |",
          "| 5 | a bank's product page | Similar | No | **High** |",
          "",
          "Three of five are passable, which is where the score comes from. It cannot see content quality — if your page is not better than #4, the score means nothing.",
        ),
      ),
    ];
  }
  if (l.includes("existing page of this website could own")) {
    return [
      tool("run_sql"),
      tool("search_page"),
      text(
        lines(
          `Nearest page for **${kw}**: ${link("/blog/invoice-payment-terms")} — it already takes 3,870 impressions a month for queries in this cluster at an average position of 11.4, and covers four of the cluster's seven keywords.`,
          "",
          "Editing it beats a new page: a new page would compete with it for the same queries. What it lacks is a comparison table and a section on which to choose; adding those is a few hundred words.",
          "",
          "Your call — if you agree, open the piece on the Content desk and ask for those two sections.",
        ),
      ),
    ];
  }
  return null;
}

export function seoAnswer(ctx: Ctx): Script | null {
  const l = ctx.lower;
  const cluster = clusterChip(ctx);
  if (cluster) return cluster;
  if (l.includes("what actually changed in the last 90 days")) return changed();
  if (l.includes("striking-distance list")) return striking();
  if (l.includes("index status record")) return invisible();
  if (l.includes("i will name a page")) {
    ctx.memory.awaiting = dropFollowUp;
    return [text("Which page? Paste its path, for example /blog/best-bookkeeping-software-freelancers.")];
  }
  if (l.includes("measured traffic") || l.includes("compare this period's traffic")) return traffic(l);
  if (l.includes("pick what this website should target next")) return targetNext();
  if (l.includes("choose a handful of seed keywords")) {
    ctx.memory.awaiting = buildClustersFollowUp;
    return [text("Which topic? A few words is enough — for example \"recurring invoices\" or \"self-employed tax\".")];
  }
  if (l.includes("search console queries")) {
    return [
      tool("run_sql"),
      clusterWrite("search_console", null, lines(
        "Built from your 2,140 Search Console queries with impressions: 386 dropped as noise (brand misspellings, one-off long tails) or off-topic, 41 clusters came out.",
        "",
        "Biggest by monthly searches: **invoice template** (22,000), **freelance tax deductions** (9,900), **quickbooks alternative** (6,600), **invoice payment terms** (4,400).",
        "",
        "They are on the SEO screen now. None is a recommendation yet — ask me what to target next when you want one.",
      )),
    ];
  }
  if (l.includes("already ranks for")) {
    return [
      tool("seo_ranked_keywords"),
      clusterWrite("ranked", null, lines(
        "Built from the 1,870 keywords ledgerly.app ranks for: 29 clusters.",
        "",
        "Worth pushing: **self employed tax calculator** (you rank 9.6, the cluster is 14k searches) and **quickbooks alternative** (11.3, 6.6k). Both sit just off page one with pages that already exist.",
        "Not worth pushing: **invoice template** — you are already 4.1 and the top three are Microsoft, Canva and Google.",
      )),
    ];
  }
  if (l.includes("two or more of my saved competitors")) {
    return [
      tool("run_sql"),
      tool("seo_ranked_keywords"),
      clusterWrite("competitor_gap", null, lines(
        "Gaps built from freshbooks.com, wave.com and bonsai.io: 640 keywords two or more of them rank for and you do not, 22 clusters.",
        "",
        "| Gap | Searches/mo | Owned by |",
        "|---|---|---|",
        "| estimate vs quote | 5,400 | FreshBooks, Wave |",
        "| freelance contract template | 4,100 | Bonsai, FreshBooks |",
        "| how to pay yourself as a freelancer | 2,900 | Wave, Bonsai |",
        "",
        "The contract template is the interesting one: you already have quote and invoice templates, so a contract template fits the set.",
      )),
    ];
  }
  if (l.includes("find the domains this website competes with")) return findCompetitors(ctx);
  if (l.includes("link to this website's saved competitors")) return findBacklinks(ctx);
  if (l.includes("saved competitors of this website and tell me which do not belong")) return cleanCompetitors(ctx);
  if (l.includes("i will name one of my competitors")) {
    ctx.memory.awaiting = (c) => [
      tool("seo_ranked_keywords"),
      tool("seo_relevant_pages"),
      text(
        lines(
          `Where **${topicFrom(c.message)}** outranks ledgerly.app (US):`,
          "",
          "| Query | Them | You | Their page |",
          "|---|---|---|---|",
          "| invoice template | 2 | 4.1 | /invoice-templates (40 templates) |",
          "| estimate vs quote | 3 | — | /blog/estimate-vs-quote |",
          "| how to write an invoice | 1 | 6.2 | /hub/invoicing/how-to-write |",
          "",
          "What their pages do that yours do not: many variants (by industry, by format) and an interactive preview. Your invoice template page is one template in three formats. Whether variants are worth building is a product call.",
        ),
      ),
    ];
    return [text("Which competitor? Name the domain, for example freshbooks.com.")];
  }
  if (l.includes("saved backlink opportunities of this website and rank them")) return rankBacklinks(ctx);
  if (l.includes("find what they link to on my competitors")) {
    return [
      tool("find_backlink_opportunities"),
      text(
        lines(
          "- **freelancersunion.org** links FreshBooks' *late payment letter* and Wave's *invoice template* from a 'Getting paid' resource list. Offer: your late payment reminder templates.",
          "- **creativeboom.com** links Bonsai and FreshBooks in 'Best invoicing apps for creatives (2026)'. Offer: a short note on why designers use Ledgerly, with the Marina Design case study.",
          "- **smallbiztrends.com** links Wave's review page. Offer: a review account, nothing else.",
          "",
          "The ask is yours to write and send; I can draft one on the Content desk if you want.",
        ),
      ),
    ];
  }
  if (l.includes("start tracking rankings and search volume")) {
    const kws = ["invoice payment terms", "freelance tax deductions", "how to invoice as a freelancer", "quickbooks import", "1099 contractor payments", "late fee on invoice", "self employed tax calculator"];
    ctx.memory.pending = () => [
      {
        kind: "write",
        tool: "track_keyword_rankings",
        input: { keywords: kws },
        apply: () => trackKeywords(kws),
        after: `Tracking ${kws.length} keywords. The first rankings arrive with the next weekly run; history builds from today.`,
        declined: "Not tracked — no credit spent.",
      },
    ];
    return [tool("run_sql"), text(`${kws.length} clusters have a winnability of 50 or more, so that is ${kws.length} main keywords. Tracking rankings and volume for them costs about $0.35 a week. Say **yes** to start.`)];
  }
  if (l.includes("ranking history of the tracked keywords")) {
    return [
      tool("run_sql"),
      tool("seo_trend"),
      text(
        lines(
          "Over the last 8 weekly runs:",
          "",
          fence("chart", chartLine("Position (lower is better)", [
            { name: "quickbooks alternative", color: "#0f766e", points: [16, 15, 15, 14, 13, 12, 12, 11] },
            { name: "best bookkeeping software", color: "#c2410c", points: [5, 5, 6, 6, 7, 8, 9, 9] },
          ], ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8"])),
          "",
          `- **Up:** ${link("/compare/quickbooks")} 16 → 11 on 'quickbooks alternative'.`,
          `- **Down:** ${link("/blog/best-bookkeeping-software-freelancers")} 5 → 9. Above you now: forbes.com/advisor (new) and a refreshed capterra.com list.`,
        ),
      ),
    ];
  }
  if (l.includes("monthly search volume of the tracked keywords")) {
    return [
      tool("seo_trend"),
      text(
        lines(
          "- **Seasonal:** 'self employed tax calculator' and 'freelance tax deductions' peak in January–April (3× the summer level), with a smaller bump before each quarterly deadline. A page should be ready by early December.",
          "- **Flat:** 'invoice payment terms', 'quickbooks alternative' — steady all year.",
          "- **Slight December dip:** everything invoicing-related, as freelancers stop billing for the holidays.",
        ),
      ),
    ];
  }
  if (l.includes("lost positions since the previous run")) {
    return [
      tool("run_sql"),
      tool("seo_relevant_pages"),
      text(
        lines(
          "Two keywords lost ground since last week:",
          "",
          "- **best bookkeeping software** 8 → 9: forbes.com/advisor/business/software/best-bookkeeping-software moved 11 → 6 after a refresh dated this month.",
          "- **late fee on invoice** 12 → 13: a new invoiced.com guide entered at 7.",
          "",
          "Neither is an emergency. The first is the dated-title problem the 90-day review already flagged.",
        ),
      ),
    ];
  }
  return null;
}
