import { addCompetitors, addKeywordClusters, call, competitorDomains, opportunityDomains, removeCompetitors, saveDeskReport, trackKeywords } from "../hooks";
import { cap, chartBars, chartLine, fence, lines, link, quoted, text, tool, topicFrom, type Ctx, type Script, type Step } from "./common";

const bare = (d: string) => d.replace(/^www\./, "").toLowerCase();

function competitorWrite(verb: "add" | "remove", domains: string[], after: string): Step {
  return {
    kind: "write",
    tool: verb === "add" ? "add_competitors" : "remove_competitors",
    input: { domains },
    apply: () => {
      if (verb === "add") addCompetitors(domains);
      else removeCompetitors(domains);
    },
    after,
    declined: "Fine — the saved competitors are unchanged.",
  };
}

function clusterWrite(source: "seeds" | "search_console" | "competitors", topic: string | null, summary: string, input: Record<string, unknown> = {}): Step {
  const tool = source === "seeds" ? "create_keyword_clusters_from_seeds" : source === "search_console" ? "create_keyword_clusters_from_search_console" : "create_keyword_clusters_from_competitors";
  return {
    kind: "write",
    tool,
    input: topic ? { seeds: topic, ...input } : input,
    apply: () => {
      addKeywordClusters(source === "competitors" ? "competitor_keywords" : source, topic);
    },
    after: summary,
    declined: "Not built — no vendor credit spent.",
  };
}

function reportWrite(title: string, answer: string): Step {
  return {
    kind: "write",
    tool: "save_report",
    input: { desk: "seo", title },
    apply: () => {
      saveDeskReport("seo", title, answer);
    },
    after: `Saved as **${title}** — it is on the Reports screen under SEO.`,
    declined: "Not saved. The plan stays in this chat.",
  };
}

function striking(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "Searches where ledgerly.app sits at position 8 or lower with more than 10 impressions and a click-through under 5%, last 28 days of Search Console:",
        "",
        "| Search | Pos. | Impr. | CTR | Page |",
        "|---|---|---|---|---|",
        `| quickbooks alternative | 11.3 | 6,210 | 1.1% | ${link("/compare/quickbooks")} |`,
        `| invoice payment terms | 11.4 | 3,870 | 0.9% | ${link("/blog/invoice-payment-terms")} |`,
        `| self employed tax calculator | 9.6 | 2,940 | 2.4% | ${link("/tools/tax-estimator")} |`,
        `| late fee on invoice | 12.8 | 1,620 | 0.6% | ${link("/blog/late-fee-invoice")} |`,
        `| freshbooks alternative | 8.9 | 1,410 | 3.8% | ${link("/compare/freshbooks")} |`,
        `| bank reconciliation | 21.4 | 1,180 | 0 clicks | ${link("/blog/bank-reconciliation-basics")} |`,
        "",
        "The first two have real demand and pages that already rank — those are the cheapest to move. Whether to strengthen them with links or with more content is yours to pick; the Site desk can suggest internal links for either.",
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

function longTailFollowUp(ctx: Ctx): Script {
  const kw = topicFrom(ctx.message).toLowerCase();
  const answer = lines(
    `What Google shows around **${kw}** (US): 8 People Also Ask questions and 10 autocomplete suggestions, turned into 14 long-tail keywords in 6 clusters.`,
    "",
    "| Cluster | Intent | Searches/mo |",
    "|---|---|---|",
    `| best ${kw} app for freelancers | commercial | 1,300 |`,
    `| ${kw} free download | transactional | 880 |`,
    `| ${kw} vs spreadsheet | commercial | 390 |`,
    `| how does ${kw} work | informational | 720 |`,
    `| is ${kw} worth it | informational | 260 |`,
    `| ${kw} for self employed | informational | 210 |`,
    "",
    "Commercial and transactional first, as asked. Two of the questions had no measurable volume and are left out.",
  );
  ctx.memory.pending = () => [
    clusterWrite("seeds", kw, `Saved the 6 clusters for **${kw}**. They are on the SEO screen.`),
  ];
  return [tool("get_search_suggestions"), tool("get_serp_results"), tool("seo_trend"), text(lines(answer, "", "Say **yes** to save these as keyword clusters (about $0.10 of vendor credit), or tell me which to drop."))];
}

function seedIdeasFollowUp(ctx: Ctx): Script {
  const kw = topicFrom(ctx.message).toLowerCase();
  ctx.memory.pending = () => [
    clusterWrite("seeds", kw, `Saved them. **${kw}** now has 11 clusters on the SEO screen.`),
  ];
  return [
    tool("seo_ranked_keywords"),
    tool("get_search_suggestions"),
    text(
      lines(
        `Related keywords for **${kw}**: 640 came back, 214 dropped as noise, and 14 clusters formed. 3 of those were off-intent (job searches and a course) and are removed, leaving 11:`,
        "",
        "- **Informational:** 6 — led by *what is " + kw + "* (2,400/mo)",
        "- **Commercial:** 3 — led by *best " + kw + " software* (1,600/mo)",
        "- **Transactional:** 2 — led by *" + kw + " template* (1,100/mo)",
        "",
        "Say **yes** to save the 11 clusters, or name the ones to leave out.",
      ),
    ),
  ];
}

function matchCompetitorFollowUp(ctx: Ctx): Script {
  const domain = bare(ctx.message.match(/[a-z0-9-]+(\.[a-z0-9-]+)+/i)?.[0] ?? "freshbooks.com");
  ctx.memory.pending = () => [
    clusterWrite("competitors", null, `Saved the 10 clusters from ${domain}. They are on the SEO screen, each as its own cluster.`, { domains: [domain] }),
  ];
  return [
    tool("seo_ranked_keywords"),
    tool("run_sql"),
    tool("search_page"),
    text(
      lines(
        `${domain} ranks for 3,420 keywords that ledgerly.app got no impressions for. After the noise filter, 10 clusters picked at random:`,
        "",
        "| Cluster | Searches/mo | Your nearest page | Suggestion | Link it from |",
        "|---|---|---|---|---|",
        `| estimate vs quote | 1,600 | ${link("/templates/quote")} | Edit — add a short comparison section | ${link("/templates/invoice")} |`,
        `| time tracking for freelancers | 2,400 | none | New page | ${link("/features/invoicing")} |`,
        `| how to send an invoice by email | 1,900 | ${link("/blog/how-to-invoice-as-a-freelancer")} | Edit — add the email step | ${link("/templates/invoice")} |`,
        `| freelance contract template | 4,400 | none | New page | ${link("/templates/quote")} |`,
        `| accounting for photographers | 880 | ${link("/for/freelancers")} | New page — the audience page is too general | ${link("/for/freelancers")} |`,
        `| client portal for freelancers | 590 | none | New page, only if the product has one | — |`,
        `| invoice in pounds | 320 | ${link("/blog/multi-currency-invoicing")} | Edit | ${link("/features/multi-currency")} |`,
        `| deposit invoice | 720 | ${link("/blog/deposit-before-starting")} | Edit — retitle around the search | ${link("/templates/invoice")} |`,
        `| retainer agreement | 1,000 | none | New page | ${link("/templates/quote")} |`,
        `| mileage deduction rate | 6,600 | ${link("/blog/deductible-expenses-freelancers")} | New page — a section will not hold it | ${link("/blog/deductible-expenses-freelancers")} |`,
        "",
        "These are suggestions; which to write is yours. Say **yes** to save the 10 as keyword clusters.",
      ),
    ),
  ];
}

const TOPIC_PLAN = (topic: string) =>
  lines(
    `**Content plan: ${topic}**`,
    "",
    `Built 9 keyword clusters for ${topic}, added 3 related ones you already had, and kept 8 that truly fit.`,
    "",
    "**Hub page (new):** " + cap(topic) + " for freelancers — targets the main cluster (5,400/mo) and links every page below.",
    "",
    "**Pages to update**",
    `- ${link("/blog/quarterly-estimated-taxes-explained")} — add the *when are quarterly taxes due* and *safe harbor rule* clusters; it already ranks 9 for the first.`,
    `- ${link("/blog/deductible-expenses-freelancers")} — add the *home office deduction* cluster as its own section.`,
    "",
    "**New pages**",
    "- How to pay quarterly taxes online — the payment steps, with screenshots.",
    "- Self-employed tax calculator guide — what each field means, linking the existing tool.",
    "- Freelance tax checklist by month — the calendar, one line per deadline.",
    "",
    "Nothing is written; this is for you to decide which pages to create.",
  );

function topicPlanFollowUp(ctx: Ctx): Script {
  const asked = typeof ctx.memory.data.topic === "string" ? ctx.memory.data.topic : ctx.message;
  const topic = topicFrom(asked).toLowerCase() || "freelance taxes";
  const plan = TOPIC_PLAN(topic);
  ctx.memory.pending = () => [reportWrite(`Content plan: ${topic}`, plan)];
  return [
    tool("create_keyword_clusters_from_seeds"),
    tool("run_sql"),
    tool("search_page"),
    text(lines(plan, "", "Say **yes** to save this plan as a report.")),
  ];
}

function topicPlanQuestions(ctx: Ctx): Script {
  ctx.memory.data.topic = ctx.message;
  ctx.memory.awaiting = topicPlanFollowUp;
  return [
    text(
      lines(
        `Before I plan **${topicFrom(ctx.message)}**, three questions:`,
        "",
        "1. What is the content for — bringing in new visitors, or helping people who already use Ledgerly?",
        "2. What should a reader be able to do after reading it?",
        "3. One page, or a series?",
      ),
    ),
  ];
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
        "They are on the SEO screen. I have not planned any.",
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

const KEYWORD_SHARERS = new Set(["canva.com"]);

const HOLDERS: Array<[string, number, string]> = [
  ["freshbooks.com", 12, "1–3"],
  ["quickbooks.intuit.com", 12, "2–5"],
  ["invoicesimple.com", 11, "3–7"],
  ["canva.com", 10, "4–8"],
  ["invoice-generator.com", 9, "5–9"],
  ["honeybook.com", 4, "8–10"],
];

function whoHolds(ctx: Ctx): Script {
  const kw = quoted(ctx.message) ?? "this keyword";
  const saved = new Set(competitorDomains().map(bare));
  const consistent = HOLDERS.filter(([, months]) => months >= 9);
  const fresh = consistent.filter(([d]) => !saved.has(d) && !KEYWORD_SHARERS.has(d)).map(([d]) => d);
  if (fresh.length) {
    ctx.memory.pending = () => [competitorWrite("add", fresh, `Saved ${fresh.join(" and ")} as competitors. Fetch their backlinks from the Competitors screen when you want them in the backlink opportunities.`)];
  }
  return [
    tool("keyword_serp_history"),
    tool("run_sql"),
    text(
      lines(
        `Twelve months of results for **${kw}** (US):`,
        "",
        "| Domain | Months in the top 10 | Usual position |",
        "|---|---|---|",
        ...HOLDERS.map(([d, m, p]) => `| ${d}${saved.has(d) ? " *(saved)*" : ""} | ${m} of 12 | ${p} |`),
        "",
        "Left out: 7 domains that appeared in only one or two months, including a forum thread and two news pieces.",
        "",
        "ledgerly.app was in the top 10 for 8 of the 12 months, mostly at 7–9, and dropped out in the two months after the March core update.",
        "",
        "canva.com holds it too, but it sells design tools; it shares the template searches, not your customers, so I would not save it.",
        "",
        fresh.length
          ? `${fresh.join(" and ")} ${fresh.length === 1 ? "holds" : "hold"} the keyword consistently but ${fresh.length === 1 ? "is" : "are"} not saved as competitors. Say **yes** to save ${fresh.length === 1 ? "it" : "them"}.`
          : "Every consistent holder is already a saved competitor.",
      ),
    ),
  ];
}

const NOT_COMPETITORS: Record<string, string> = {
  "bench.co": "sells a bookkeeper, not software — a different buyer making a different decision",
  "nerdwallet.com": "reviews every tool; it shares keywords, not customers",
  "indy.fyi": "a French-market tool; it shares English keywords only through its blog",
  "invoicesimple.com": "an invoice app with no bookkeeping — it overlaps on templates only",
};

function cleanCompetitors(ctx: Ctx): Script {
  const list = competitorDomains();
  const flagged = list.filter((d) => NOT_COMPETITORS[bare(d)]);
  const steps: Step[] = [tool("run_sql"), tool("seo_ranked_keywords")];
  if (flagged.length === 0) return [...steps, text(`All ${list.length} saved competitors sell what you sell to the same buyer. Nothing to remove.`)];
  ctx.memory.pending = () => [competitorWrite("remove", flagged, `Removed ${flagged.join(", ")} from competitors, with the backlinks fetched for them.`)];
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

const LINK_REASONS: Record<string, string> = {
  "fitsmallbusiness.com": "links FreshBooks, QuickBooks, Wave and Bonsai from *Best invoicing software* — a roundup that is refreshed every year. Offer: a reviewer account and the comparison table from /compare/freshbooks.",
  "business.org": "links three of them from *Best accounting software for freelancers*. Offer: the same — they add tools when asked by a vendor with a free tier.",
  "freelancersunion.org": "links FreshBooks' late payment letter and Wave's invoice template from a *Getting paid* resource page. Offer: your late payment reminder template, which is free and has no signup wall.",
  "creativeboom.com": "links Bonsai and FreshBooks in *Best invoicing apps for creatives*. Offer: a short note on why designers use Ledgerly.",
  "smallbiztrends.com": "links Wave's review page. The link is nofollow; a review account is the only ask.",
  "aiga.org": "links FreshBooks and Bonsai from its design business resources. Offer: the hourly rate calculator, which fits the page better than the product.",
};

function whyTheyLink(): Script {
  const top = opportunityDomains().filter((d) => LINK_REASONS[d]).slice(0, 5);
  return [
    tool("list_backlink_opportunities"),
    tool("run_sql"),
    text(
      lines(
        top.length ? "What the top backlink opportunities link to on your competitors, and why:" : "No backlink opportunities yet — fetch a saved competitor's backlinks on the Competitors screen first.",
        "",
        ...top.map((d) => `- **${d}** ${LINK_REASONS[d]}`),
        "",
        top.length ? "Writing and sending each ask is yours; the Content desk can help you draft one." : "",
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

function trackMainKeywords(ctx: Ctx): Script {
  const kws = ["invoice payment terms", "freelance hourly rate calculator", "late payment reminder email", "freshbooks alternative", "how to record stripe fees", "wave accounting alternative", "quickbooks alternative"];
  ctx.memory.pending = () => [
    {
      kind: "write",
      tool: "track_keyword_volumes",
      input: { keywords: kws },
      apply: () => trackKeywords(kws),
      after: `Recorded 12 months of search volume for the ${kws.length} keywords in each of your markets. They are on the Tracked screen; ask whether demand is seasonal when you want a read.`,
      declined: "Not tracked — no credit spent.",
    },
  ];
  return [tool("run_sql"), text(`${kws.length} clusters are marked hot or warm, so that is ${kws.length} main keywords. Recording their search volume costs about $0.05 per market. Say **yes** to start.`)];
}

function movers(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "Search Console position for the tracked keywords, month by month (US):",
        "",
        fence("chart", chartLine("Position (lower is better)", [
          { name: "quickbooks alternative", color: "#0f766e", points: [13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 8, 8] },
          { name: "best bookkeeping software for freelancers", color: "#c2410c", points: [24, 22, 21, 20, 19, 19, 18, 17, 17, 16, 19, 16] },
          { name: "home office deduction", color: "#7c3aed", points: [17, 17, 18, 18, 19, 19, 20, 21, 21, 22, 19, 23] },
        ], ["N", "D", "J", "F", "M", "A", "M", "J", "J", "A", "S", "O"])),
        "",
        `- **Up most:** ${link("/compare/quickbooks")} 13 → 8 over twelve months, steady, no single jump.`,
        `- **Up, unevenly:** ${link("/blog/best-bookkeeping-software-freelancers")} 24 → 16, with a dip in September.`,
        `- **Down most:** ${link("/blog/home-office-deduction")} 17 → 23 since April. The UK market shows no movers worth naming.`,
        "",
        "The data shows when each moved, not why. The home office page last changed 14 months ago; whether to refresh it is your call.",
      ),
    ),
  ];
}

function seasonal(): Script {
  return [
    tool("run_sql"),
    tool("seo_trend"),
    text(
      lines(
        "- **Seasonal:** 'quarterly estimated taxes', 'freelance tax deductions' and '1099-nec' peak in January–April (3× the summer level), with smaller bumps before each quarterly deadline. A page should be ready by early December.",
        "- **Flat:** 'invoice payment terms', 'quickbooks alternative' — steady all year.",
        "- **Slight December dip:** everything invoicing-related, as freelancers stop billing for the holidays.",
      ),
    ),
  ];
}

export function seoAnswer(ctx: Ctx): Script | null {
  const l = ctx.lower;
  const cluster = clusterChip(ctx);
  if (cluster) return cluster;
  if (l.includes("twelve months of results-page history")) return whoHolds(ctx);
  if (l.includes("position 8 or lower")) return striking();
  if (l.includes("index status record")) return invisible();
  if (l.includes("i will name a page")) {
    ctx.memory.awaiting = dropFollowUp;
    return [text("Which page? Paste its path, for example /blog/best-bookkeeping-software-freelancers.")];
  }
  if (l.includes("measured traffic") || l.includes("compare this period's traffic")) return traffic(l);
  if (l.includes("people also ask questions")) {
    ctx.memory.awaiting = longTailFollowUp;
    return [text("Which keyword? For example \"invoice template\" or \"freelance taxes\".")];
  }
  if (l.includes("i will give you a seed keyword or topic")) {
    ctx.memory.awaiting = seedIdeasFollowUp;
    return [text("Which seed? A keyword or a topic, for example \"expense tracking\".")];
  }
  if (l.includes("i will name a competitor's domain")) {
    ctx.memory.awaiting = matchCompetitorFollowUp;
    return [text("Which competitor? Name the domain, for example freshbooks.com.")];
  }
  if (l.includes("i will give you a topic. before you start")) {
    ctx.memory.awaiting = topicPlanQuestions;
    return [text("Which topic? A few words is enough — for example \"freelance taxes\".")];
  }
  if (l.includes("choose a handful of seed keywords")) {
    ctx.memory.awaiting = buildClustersFollowUp;
    return [text("Which topic? A few words is enough — for example \"recurring invoices\" or \"self-employed tax\".")];
  }
  if (l.includes("search console queries")) {
    ctx.memory.pending = () => [
      clusterWrite("search_console", null, lines(
        "Built from your 2,140 Search Console queries with impressions: 386 dropped as noise (brand misspellings, one-off long tails) or off-topic, 41 clusters came out.",
        "",
        "Biggest by monthly searches: **invoice template** (22,000), **freelance tax deductions** (9,900), **quickbooks alternative** (6,600), **invoice payment terms** (4,400).",
        "",
        "They are on the SEO screen now. None is a recommendation yet.",
      )),
    ];
    return [tool("run_sql"), text("2,140 Search Console queries have impressions in the last 28 days. Clustering them spends about $0.60 of vendor credit. Say **yes** to build the clusters.")];
  }
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
  if (l.includes("find what they link to on my competitors")) return whyTheyLink();
  if (l.includes("start tracking search volume for the main keyword")) return trackMainKeywords(ctx);
  if (l.includes("search console position for the tracked keywords")) return movers();
  if (l.includes("monthly search volume of the tracked keywords")) return seasonal();
  return null;
}
