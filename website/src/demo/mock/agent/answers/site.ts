import type { LinkSuggestion, PillarSuggestion } from "@demo/lib/types";
import { ORIGIN, PAGES, SITE_ID } from "../../data/site";
import { uid } from "../channel";
import { addLinkSuggestions, addPillarSuggestions, call } from "../hooks";
import { cap, isYes, lines, link, page, text, tool, tools, topicFrom, type Ctx, type Script, type Step } from "./common";

const live = () => PAGES.filter((p) => p.status === 200);

function noteStep(ctx: Ctx, note: string, after: string): Step {
  return {
    kind: "write",
    tool: "save_note",
    input: { note },
    apply: () => {
      call("POST", "/api/v1/notes", { note, kind: "note", siteId: ctx.siteId ?? SITE_ID });
    },
    after,
    declined: "Fine — nothing saved. The summary stays here in the chat if you want to copy any of it.",
  };
}

function profile(ctx: Ctx): Script {
  const summary =
    "Ledgerly sells bookkeeping software to freelancers and very small teams: invoicing, expense tracking with receipts, bank feeds, quarterly tax estimates and plain reports. Three plans — Solo $12, Team $29, Studio $59 a month, no per-seat fees. The site leans on a weekly blog about getting paid and self-employed tax, a public help centre, free templates and tools, and comparison pages against QuickBooks, FreshBooks, Wave, Xero and Bonsai.";
  ctx.memory.pending = () => [
    noteStep(ctx, `Site profile: ${summary}`, "Saved as a note on this website. Every task on this site can read it from now on, and you can edit or delete it on the Notes screen."),
  ];
  return [
    ...tools("search_page", "search_page"),
    tool("Task"),
    text(
      lines(
        "I searched the crawled corpus for what the site says about itself and opened the four pages that decide it: the home page, /pricing, /features/invoicing and /about.",
        "",
        "**What Ledgerly is, from its own pages**",
        "",
        `> ${summary}`,
        "",
        "**Covered well**",
        "- Getting paid — 9 posts on invoicing, reminders, deposits and late fees, plus 2 templates and the invoice generator.",
        "- Self-employed tax — /features/tax, the tax estimator and six posts (quarterly estimates, 1099-NEC, home office, deductions).",
        "- Switching — five comparison pages and two listicles.",
        "",
        "**Covered thinly**",
        `- Mileage (${link("/features/mileage")}, 260 words, no meta description) and multi-currency (${link("/features/multi-currency")}, 330 words).`,
        "- Teams — the Team and Studio plans exist on /pricing, but no page explains what a team of three gets over Solo.",
        "",
        "**Never mentioned**",
        "- Payroll, VAT/GST outside the US, inventory. Pricing says \"US and Canada\" once; nothing else says where Ledgerly works.",
        "",
        "Where the evidence is thin I left it out: no page states a customer count, so the summary does not claim one.",
        "",
        "Say **yes** and I will keep this as a note on the website so every desk starts from it.",
      ),
    ),
  ];
}

function gaps(): Script {
  return [
    ...tools("search_page", "search_page", "search_page"),
    text(
      lines(
        "I ran eleven searches over the 164 pages the crawl has read. These are topics a freelancer comparing bookkeeping tools would expect and find nothing on:",
        "",
        "| Topic | Closest passage on the site | Where |",
        "|---|---|---|",
        `| Paying contractors / 1099 *issuing* | "The 1099-NEC is the form a client sends you…" — written for the receiver, not the sender | ${link("/blog/1099-nec-guide")} |`,
        `| Sales tax / VAT outside the US | "Ledgerly works for businesses in the US and Canada." | ${link("/pricing")} |`,
        `| Moving data in from QuickBooks | "Import transactions from any CSV export." | ${link("/docs/import-transactions-csv")} |`,
        `| What the Team plan adds | "Team — up to 5 people, $29." Nothing explains roles or permissions. | ${link("/pricing")} |`,
        `| Mobile app | One line in the changelog: "Receipt capture on iOS." | ${link("/changelog")} |`,
        "",
        "Two caveats before you call these gaps:",
        "- The crawl did not read anything behind /app/ (robots disallows it), so in-product help is invisible to me.",
        `- ${link("/docs")} links 24 articles and all were read, so the help centre is complete — the migration gap is real, not a crawl hole.`,
        "",
        "The QuickBooks import is the one I would look at first: 'quickbooks alternative' already brings impressions to the comparison page, and that reader's next question is how to move.",
      ),
    ),
  ];
}

function broken(): Script {
  return [
    tool("run_sql"),
    tool("search_page"),
    text(
      lines(
        "From the last crawl's status codes, two different problems:",
        "",
        "**Gone (404 / 410) — fix the links pointing at them**",
        `- ${link("/blog/2023-launch-post")} → 404. Still in sitemap.xml, linked from ${link("/about")} ("read the launch post") and ${link("/changelog")}.`,
        `- ${link("/features/projects")} → 410. A removed feature; still listed in the sitemap and linked from ${link("/for/consultants")}.`,
        "",
        "**Redirects in the sitemap — not broken, but wasteful**",
        `- ${link("/old-pricing")} → 301 to /pricing. The sitemap should list /pricing, not the old URL.`,
        "",
        "**Refused or unreachable** — none this crawl. Every live page answered 200 to the crawler. PerplexityBot does get a 403 from a Cloudflare bot rule on the home page; that is a choice, not a fault, and it is on the Site screen under crawler access.",
        "",
        "Suggested fixes, smallest first: drop the three URLs from the sitemap, repoint the /about link to the changelog entry for the launch, and remove the /features/projects link from /for/consultants. Each is a two-minute edit in your CMS — I have not changed anything.",
      ),
    ),
  ];
}

function sitemap(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "The sitemap lists 118 URLs; the crawl reached 164 pages by following links.",
        "",
        "**In the sitemap but dead**",
        `- ${link("/blog/2023-launch-post")} (404), ${link("/features/projects")} (410), ${link("/old-pricing")} (301 → /pricing).`,
        "",
        "**Found by links, missing from the sitemap**",
        "",
        "| Page | Worth listing? | Why |",
        "|---|---|---|",
        `| ${link("/blog/page/2")}, ${link("/blog/page/3")} | No | Pagination. Crawlers find it from /blog; listing it adds nothing. |`,
        `| ${link("/blog/tag/taxes")}, ${link("/blog/tag/invoicing")} | No | Already noindex. Leave them out. |`,
        `| ${link("/status")} | No | 90 words of uptime status — not a search page. |`,
        `| 12 help-centre articles under /docs/ | **Yes** | Real answers ("Automatic payment reminders", "Accept online payments") that search for how-to queries. |`,
        "",
        "So the one change worth making is to add the help centre to the sitemap and drop the three dead URLs. Whether help articles should rank at all is your call; some teams prefer people land on the marketing pages.",
      ),
    ),
  ];
}

function thin(): Script {
  return [
    tool("run_sql"),
    ...tools("search_page", "search_page"),
    text(
      lines(
        "I sorted the read pages by word count and opened the six under 300 words that are not utility pages:",
        "",
        "| Page | Words | Suggestion |",
        "|---|---|---|",
        `| ${link("/webinars/pricing-your-work")} | 170 | **Merge** into /blog/hourly-vs-project-pricing — it is a recording link and two lines. It is also an orphan. |`,
        `| ${link("/webinars/quarterly-taxes-2026")} | 190 | **Write out** — the session covered due dates people search for every quarter; a transcript summary would earn its keep. |`,
        `| ${link("/features/mileage")} | 260 | **Write out** — a product page with no meta description competing with a better-written blog post on mileage logs. |`,
        `| ${link("/tools/invoice-generator")} | 300 | **Leave** — the tool is the content; the words count misses it. |`,
        `| ${link("/press")} | 260 | **Leave** — noindex already, which is right. |`,
        `| ${link("/status")} | 90 | **Leave** — utility. |`,
        "",
        "If you want one to start with, /features/mileage: it is in the main navigation, so every visitor who clicks it gets the thinnest page on the site.",
      ),
    ),
  ];
}

function coveredFollowUp(ctx: Ctx): Script {
  const topic = topicFrom(ctx.message);
  const words = topic.toLowerCase().split(/\W+/).filter((w) => w.length > 3);
  const hits = live()
    .map((p) => ({ p, score: words.filter((w) => `${p.title ?? ""} ${p.metaDescription ?? ""}`.toLowerCase().includes(w)).length }))
    .filter((h) => h.score > 0)
    .sort((a, c) => c.score - a.score)
    .slice(0, 3);
  const verdict = hits.length === 0 ? "absent" : hits[0].score >= Math.max(1, words.length - 1) ? "covered" : "half covered";
  const rows = hits.map(({ p }) => {
    const path = new URL(p.url).pathname;
    return `- ${link(path)} — "${(p.bodyText ?? p.title ?? "").split(". ")[0].slice(0, 140)}…"`;
  });
  return [
    ...tools("search_page", "search_page"),
    text(
      lines(
        `**${cap(topic)}: ${verdict}.**`,
        "",
        hits.length > 0 ? "The closest passages:" : "No passage on the 164 read pages discusses it; the nearest hits only share a word.",
        ...rows,
        "",
        verdict === "covered"
          ? "A new page would mostly repeat what is there. Extending the strongest one is the safer move."
          : verdict === "half covered"
            ? "These touch the topic without answering it. A new page could own it — link it from the first one above so they do not compete."
            : "A new page would not duplicate anything you have.",
      ),
    ),
  ];
}

function fixFirst(): Script {
  return [
    tool("run_sql"),
    ...tools("search_page", "search_page"),
    text(
      lines(
        "Ordered by what each one costs Ledgerly, not by page count:",
        "",
        `1. **Sitemap lists dead and redirected URLs** (3 URLs). Cheap to fix, and it is the first thing Google reads. ${link("/blog/2023-launch-post")}, ${link("/features/projects")}, ${link("/old-pricing")}.`,
        `2. **Orphan pages** (3). ${link("/compare/bonsai")} has no inlinks at all — a comparison page nobody can reach is a page that cannot rank. ${link("/dpa")} and ${link("/webinars/pricing-your-work")} matter less.`,
        "3. **Missing meta descriptions on product pages** (2): /features/mileage and /features/multi-currency. Google writes its own snippet from nav text today.",
        "4. **Trailing-slash duplicate**: /pricing/ answers 200 with a canonical to /pricing. Harmless because of the canonical; fix it in the server config when convenient.",
        "",
        "**Cosmetic — I would turn these down:**",
        "- Title over 60 characters on 14 blog posts. They truncate in results but still rank; rewriting 14 titles is not worth it.",
        "- Images missing alt text (9) on decorative illustrations.",
        "",
        "Say which to turn down and I will mark them rejected so they stop showing as open. Nothing changes on the site itself.",
      ),
    ),
  ];
}

function explainFollowUp(ctx: Ctx): Script {
  const check = topicFrom(ctx.message);
  return [
    tool("run_sql"),
    ...tools("search_page", "search_page"),
    text(
      lines(
        `**${cap(check)}**`,
        "",
        "I read the pages it flagged before answering. What the check measures: whether each page carries the signal search engines use to choose and describe it, and it fires when the page either lacks it or contradicts itself.",
        "",
        `On Ledgerly it lands mostly on product pages deep in the navigation — ${link("/features/mileage")} and ${link("/features/multi-currency")} — which are exactly the pages with the least text, so search engines have the least to go on there.`,
        "",
        "A fix on those pages would look like: one specific sentence on what the feature does for a freelancer, written for the page rather than copied from the nav. It is a ten-minute edit per page, and you can draft it on the Content desk if you want help with the wording.",
      ),
    ),
  ];
}

function rendering(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "From the desktop and mobile render records:",
        "",
        "- **Most of the site is server-rendered.** On 46 of 52 rendered pages the text, links and title in the raw HTML match what the browser shows. A crawler that never runs JavaScript sees the same page you do.",
        `- **The pricing toggle is the exception.** ${link("/pricing")} renders monthly prices in HTML, but the annual prices and the plan comparison table only appear after a script runs. An AI crawler quoting your prices will only ever see monthly.`,
        `- **Template downloads.** ${link("/templates/invoice")} and ${link("/templates/receipt")} inject their download links client-side; without JavaScript there is no link to the PDF at all.`,
        "- **Desktop vs mobile:** the mobile render drops the footer links to /partners and /security behind a collapsed menu that is in the DOM, so nothing is lost for crawlers.",
        "",
        "Nothing here says the site depends on client-side rendering. Two components do; moving the annual prices and the download links into the HTML would close the gap.",
      ),
    ),
  ];
}

interface Strategy {
  key: string;
  kind: "links" | "removals" | "pillars";
  generator: string;
  rows: Array<[string, string, string, string, string]>;
  pillars?: Array<{ action: "create" | "expand"; topic: string; covering?: string; members: string[]; suggestion: string }>;
}

const STRATEGIES: Strategy[] = [
  {
    key: "related content",
    kind: "links",
    generator: "propose_links_from_table",
    rows: [
      ["/blog/invoice-payment-terms", "/blog/late-fee-invoice", "The section on net 15 vs net 30 ends where the late-fee post begins. Link \"what happens when the date passes\" to it.", "Picking your terms", "what happens when the date passes"],
      ["/blog/deposit-before-starting", "/blog/scope-creep", "Both posts are about protecting a project before it starts. Link \"scope\" in the deposit wording section.", "The wording", "scope"],
      ["/blog/quarterly-estimated-taxes-explained", "/blog/home-office-deduction", "The paragraph listing what lowers the estimate names the home office deduction without linking the post that explains it.", "Lowering the number", "home office deduction"],
      ["/blog/cash-flow-forecast-small-business", "/blog/freelance-emergency-fund", "The forecast post tells readers to keep a buffer; the emergency-fund post says how big.", "When the forecast goes red", "a buffer"],
    ],
  },
  {
    key: "authority to money pages",
    kind: "links",
    generator: "propose_links_from_table",
    rows: [
      ["/templates/invoice", "/features/invoicing", "The invoice template is the strongest page on the site (link score 71). Its closing section suggests sending invoices online — that is the invoicing page.", "Sending it", "send invoices online"],
      ["/blog/deductible-expenses-freelancers", "/features/expenses", "Readers of the deductions post are told to keep receipts; the expenses page is where that happens.", "Keep the proof", "keep every receipt"],
      ["/tools/tax-estimator", "/features/tax", "The estimator gives one number; the tax feature keeps it current every quarter. One sentence under the result would carry the reader there.", "Your estimate", "every quarter"],
    ],
  },
  {
    key: "orphan and deep page rescue",
    kind: "links",
    generator: "propose_links_from_table",
    rows: [
      ["/compare/quickbooks", "/compare/bonsai", "Bonsai has no inlinks at all. The QuickBooks comparison already lists 'other tools freelancers consider' — Bonsai belongs there.", "Other tools", "Bonsai"],
      ["/blog/hourly-vs-project-pricing", "/webinars/pricing-your-work", "The orphaned webinar is on exactly this subject. A one-line 'watch the session' link rescues it.", "What the numbers say", "the pricing webinar"],
    ],
  },
  {
    key: "unlinked mentions",
    kind: "links",
    generator: "propose_unlinked_mentions",
    rows: [
      ["/blog/best-bookkeeping-software-freelancers", "/pricing", "\"Ledgerly costs $12 a month\" names the pricing page's subject word for word and does not link it.", "7. Ledgerly", "$12 a month"],
      ["/blog/1099-nec-guide", "/tools/tax-estimator", "\"self-employed tax estimator\" appears in the last paragraph as plain text.", "After you file", "self-employed tax estimator"],
      ["/blog/recurring-invoices", "/docs/recurring-invoices", "The post says \"set up recurring invoices in Ledgerly\" without pointing at the help article that shows how.", "Setting it up", "set up recurring invoices"],
    ],
  },
  {
    key: "freshness",
    kind: "links",
    generator: "propose_links_from_table",
    rows: [
      ["/blog/how-to-invoice-as-a-freelancer", "/blog/invoice-numbering", "The newest invoicing post has two inlinks. The main how-to already discusses numbering in passing.", "Step 3: numbering", "number every invoice"],
      ["/blog/quickbooks-alternatives", "/blog/xero-vs-ledgerly", "The new Xero comparison is not linked from the alternatives list that names Xero.", "4. Xero", "Xero"],
    ],
  },
  {
    key: "site skeleton",
    kind: "links",
    generator: "propose_hierarchy_links",
    rows: [
      ["/templates", "/templates/late-payment-reminder", "The templates hub links six of its seven children; the reminder emails page is missing. This belongs in the hub's list, not body copy.", "All templates", "Late payment reminder emails"],
      ["/", "/security", "Home links every utility page in the footer except /security. Footer link.", "Footer", "Security"],
    ],
  },
  {
    key: "prune off-topic links",
    kind: "removals",
    generator: "propose_link_removals",
    rows: [
      ["/blog/profit-first-for-freelancers", "/compare/wave", "The anchor \"free tools\" sits in a paragraph about bank accounts; the Wave comparison is not about either. A reader following it would feel misdirected.", "Set up the accounts", "free tools"],
      ["/blog/client-onboarding-questionnaire", "/features/bank-feeds", "\"connect everything\" in a questionnaire post points at bank feeds; the passage is about client tools.", "Before the kickoff", "connect everything"],
    ],
  },
  {
    key: "thin out over-linked pages",
    kind: "removals",
    generator: "propose_link_removals",
    rows: [
      ["/blog/accounting-terms-glossary", "/pricing", "The glossary has 31 body links against a budget of 15; this is the third link to /pricing on the page, with the anchor \"here\".", "A–C", "here"],
      ["/blog/accounting-terms-glossary", "/features/reports", "Second link to /features/reports in the same section, anchor \"read more\".", "P–R", "read more"],
    ],
  },
  {
    key: "dead-end targets",
    kind: "removals",
    generator: "propose_link_removals",
    rows: [
      ["/for/consultants", "/features/projects", "Links to /features/projects, which returns 410. Drop the link — the feature is gone.", "Run the whole engagement", "projects"],
      ["/about", "/blog/2023-launch-post", "Links to a 404. Repoint it to the changelog entry for the launch rather than drop it.", "Our story", "read the launch post"],
    ],
  },
  {
    key: "pillar pages from meaning",
    kind: "pillars",
    generator: "propose_pillar_pages",
    rows: [],
    pillars: [
      {
        action: "create",
        topic: "Cash flow for freelancers",
        members: ["/blog/cash-flow-forecast-small-business", "/blog/freelance-emergency-fund", "/blog/profit-first-for-freelancers", "/templates/cash-flow", "/blog/separate-business-bank-account"],
        suggestion: "Five pages on keeping money in the bank and no page that introduces them. A pillar at /guides/cash-flow should cover forecasting, buffers and separate accounts in that order, link each member once, and every member should link back from its intro.",
      },
    ],
  },
  {
    key: "section index pages",
    kind: "pillars",
    generator: "propose_pillar_pages",
    rows: [],
    pillars: [
      {
        action: "create",
        topic: "Webinars",
        members: ["/webinars/quarterly-taxes-2026", "/webinars/pricing-your-work"],
        suggestion: "/webinars/ holds pages but nothing lives at /webinars itself. An index page that lists each session with a two-line summary and its date would give the folder a front door.",
      },
    ],
  },
  {
    key: "pillar pages from search demand",
    kind: "pillars",
    generator: "propose_pillar_pages",
    rows: [],
    pillars: [
      {
        action: "create",
        topic: "invoice payment terms",
        members: ["/blog/invoice-payment-terms", "/blog/late-fee-invoice", "/blog/how-to-invoice-as-a-freelancer", "/templates/invoice"],
        suggestion: "\"invoice payment terms\" takes impressions on four pages and the best ranks 11.4. A single page that owns the query should define net 15/30/60, say which to pick, and hand off to the template; /blog/invoice-payment-terms contributes the definitions, the late-fee post the consequences, the template the wording.",
      },
    ],
  },
];

function strategyFor(lower: string): Strategy | null {
  return STRATEGIES.find((s) => lower.includes(`strategy: ${s.key}`)) ?? null;
}

function runStrategy(ctx: Ctx, s: Strategy): Script {
  const jobId = uid("job");
  const at = new Date().toISOString();
  const pillar = s.kind === "pillars";
  const review = pillar ? "review_pillar_suggestions" : "review_link_suggestions";
  const total = pillar ? (s.pillars?.length ?? 0) + 3 : s.rows.length + 3;
  const kept = pillar ? (s.pillars?.length ?? 0) : s.rows.length;

  const apply = () => {
    if (pillar) {
      const rows: PillarSuggestion[] = (s.pillars ?? []).map((p, i) => ({
        id: uid("ps"),
        createdAt: at,
        updatedAt: at,
        siteId: ctx.siteId ?? SITE_ID,
        jobId,
        action: p.action,
        topic: p.topic,
        memberPageIds: p.members.map((m) => page(m).id),
        coveringPageId: p.covering ? page(p.covering).id : null,
        coveringUrl: p.covering ? `${ORIGIN}${p.covering}` : null,
        state: "review_approved",
        suggestion: p.suggestion,
        searchScore: 0.78 - i * 0.04,
        confidence: 0.84 - i * 0.03,
        score: 0.81 - i * 0.04,
        members: p.members.map((m) => ({ id: page(m).id, url: `${ORIGIN}${m}`, title: page(m).title })),
      }));
      addPillarSuggestions(rows);
      return;
    }
    const rows: LinkSuggestion[] = s.rows.map(([from, to, suggestion, heading, anchor], i) => ({
      id: uid("ls"),
      createdAt: at,
      updatedAt: at,
      siteId: ctx.siteId ?? SITE_ID,
      jobId,
      fromPageId: page(from).id,
      fromChunkId: uid("ch"),
      toPageId: page(to).id,
      action: s.kind === "removals" ? "delete" : "create",
      state: "review_approved",
      suggestion,
      searchScore: 0.71 - i * 0.03,
      confidence: 0.86 - i * 0.04,
      score: 0.8 - i * 0.04,
      fromUrl: `${ORIGIN}${from}`,
      toUrl: `${ORIGIN}${to}`,
      fromChunkHeading: heading,
      fromChunkOrdinal: 2 + i,
      fromChunkText: null,
      anchor,
    }));
    addLinkSuggestions(rows);
  };

  const listed = pillar
    ? (s.pillars ?? []).map((p) => `- **${p.action === "create" ? "New pillar" : "Expand"}: ${p.topic}** — ${p.members.length} member pages. ${p.suggestion}`)
    : s.rows.map(([from, to, , , anchor]) => `- ${s.kind === "removals" ? "Remove" : "Add"} ${link(from)} → ${link(to)} on "${anchor}"`);

  const steps: Step[] = [
    tool("run_sql"),
    {
      kind: "write",
      tool: "start_structure_job",
      input: { strategy: s.key },
      apply: () => {},
      after: "",
      declined: "Understood — no job started and nothing was written. The strategy is still here if you want to run it later.",
    },
  ];
  return [
    ...steps,
    { kind: "tool", name: s.generator, ms: 1400 },
    tool(pillar ? "screen_pillar_suggestions" : "screen_link_suggestions"),
    { kind: "progress", tool: review, total },
    tool(pillar ? "rank_pillar_suggestions" : "rank_link_suggestions"),
    {
      kind: "write",
      tool: "finish_structure_job",
      input: { job_id: jobId },
      apply,
      after: () =>
        lines(
          `The **${s.key}** job finished. The generator proposed ${total + 2}, screening dropped 2, and review kept ${kept} of ${total} — each kept one has a sentence you can point to on the source page.`,
          "",
          ...listed,
          "",
          pillar
            ? "They are on the Structure screen under pillar suggestions, each with its member pages. Approve, edit or turn down each one — nothing on the site changes until you build the page."
            : "They are on the Structure screen with the passage each link would sit in. Approve or turn down each one; you make the edit in your CMS. Refresh the list if it is already open.",
        ),
      declined: "Stopped before saving — the job's candidates were discarded and nothing reached the Structure screen.",
    },
  ];
}

export function siteAnswer(ctx: Ctx): Script | null {
  const l = ctx.lower;
  const s = strategyFor(l);
  if (s) return runStrategy(ctx, s);
  if (l.includes("write down what this business actually is")) return profile(ctx);
  if (l.includes("tell me the gaps")) return gaps();
  if (l.includes("read the crawl status")) return broken();
  if (l.includes("sitemap does not list")) return sitemap();
  if (l.includes("carry almost nothing")) return thin();
  if (l.includes("i will name a topic. search what the site")) {
    ctx.memory.awaiting = coveredFollowUp;
    return [text("Which topic? Name it in a few words — for example \"paying contractors\" or \"VAT for EU clients\" — and I will search what the site already says.")];
  }
  if (l.includes("technical checks that are open")) return fixFirst();
  if (l.includes("i will name one of the open checks")) {
    ctx.memory.awaiting = explainFollowUp;
    return [tool("run_sql"), text("Which check? The open ones are listed on the Technical SEO screen — paste its name and I will read the pages it flagged before explaining it.")];
  }
  if (l.includes("rendering findings")) return rendering();
  return null;
}

export function pagesFallback(ctx: Ctx): Script {
  if (isYes(ctx.lower)) return [text("There is nothing waiting for a yes in this task. Ask me about a page or a topic and I will search what the crawl read.")];
  return coveredFollowUp(ctx);
}
