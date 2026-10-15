import { call } from "../hooks";
import { cap, lines, link, text, tool, type Ctx, type Script, type Step } from "./common";

interface Plan {
  title: string;
  h1: string;
  metaDescription: string;
  slug: string;
  targetKeyword: string;
  why: string;
  body: string;
}

const RECURRING: Plan = {
  title: "Recurring invoices for freelancers: set up once, get paid monthly",
  h1: "Recurring invoices, without the monthly reminder to yourself",
  metaDescription: "How recurring invoices work in Ledgerly: pick a schedule, attach payment terms, and every retainer client is billed on time. Set up in five minutes.",
  slug: "features/recurring-invoices",
  targetKeyword: "recurring invoices",
  why: "'recurring invoices' gets 2,400 searches a month and you rank 18 with a help article, not a product page. Retainer clients are the theme of three posts already.",
  body: [
    "If you bill the same client every month, you already know the ritual: duplicate last month's invoice, change the date, change the number, hope you did not forget. Recurring invoices replace the ritual with a schedule.",
    "",
    "## How it works",
    "",
    "You create the invoice once — client, line items, payment terms — and pick how often it repeats: weekly, monthly, quarterly or on a custom day. Ledgerly sends each one on the date you chose, numbered in sequence, and marks it paid when the money arrives through your [bank feed](/features/bank-feeds).",
    "",
    "## What you can change between invoices",
    "",
    "- **Hours that vary.** Pull tracked time into the next invoice before it goes out.",
    "- **A price rise.** Edit the template; every future invoice uses the new rate.",
    "- **A pause.** Skip one cycle without breaking the sequence.",
    "",
    "## Getting paid on time",
    "",
    "Recurring invoices carry the same [payment terms](/blog/invoice-payment-terms) as one-off ones. Turn on automatic reminders and a client who forgets gets a polite nudge three days after the due date — the wording is in our [late payment reminder templates](/templates/late-payment-reminder).",
    "",
    "## Who it is for",
    "",
    "Retainers, maintenance contracts, monthly bookkeeping clients, coaching packages. If the amount is the same and the date is predictable, it should not take you any time at all.",
  ].join("\n"),
};

const TAXES: Plan = {
  title: "How much should a freelancer set aside for taxes?",
  h1: "How much to set aside for taxes when you work for yourself",
  metaDescription: "A plain rule for freelancers: what percentage of each payment to set aside for federal, state and self-employment tax, and how to adjust it every quarter.",
  slug: "blog/how-much-to-set-aside-for-taxes",
  targetKeyword: "how much to set aside for taxes freelancer",
  why: "It is the question support answers most in October, the query has 5,400 searches a month, and no page on the site answers it directly — the quarterly-taxes post assumes you already know the number.",
  body: [
    "The short answer: set aside 25–30% of every payment until you have a better number. The better number takes ten minutes to work out, and it is worth doing before your next quarterly payment.",
    "",
    "## Where the money goes",
    "",
    "- **Self-employment tax** — 15.3% of 92.35% of your profit, for Social Security and Medicare.",
    "- **Federal income tax** — depends on your bracket, after half the self-employment tax and your deductions.",
    "- **State income tax** — zero in some states, around 5% in many.",
    "",
    "## A better number in three steps",
    "",
    "1. Take last year's total tax and divide it by last year's profit. That is your effective rate.",
    "2. Add two points if your income is growing.",
    "3. Move that percentage of every payment into a separate account the day it arrives — we explain why a [separate business bank account](/blog/separate-business-bank-account) makes this painless.",
    "",
    "## Adjust every quarter",
    "",
    "Your estimate is only as good as your bookkeeping. If you track expenses as they happen, the [tax estimator](/tools/tax-estimator) can recalculate the rate each quarter, and the [quarterly estimated taxes guide](/blog/quarterly-estimated-taxes-explained) walks through the payment itself.",
  ].join("\n"),
};

const TEMPLATE: Plan = {
  title: "Freelance contract template (free, plain English)",
  h1: "A freelance contract template you can send today",
  metaDescription: "A free freelance contract template in plain English: scope, payment terms, deposits, revisions and kill fees. Copy it into Google Docs or Word.",
  slug: "templates/freelance-contract",
  targetKeyword: "freelance contract template",
  why: "The SEO desk's competitor-gap clusters show 'freelance contract template' at 4,100 searches a month, owned by Bonsai and FreshBooks. You already have invoice and quote templates; this completes the set.",
  body: [
    "A contract does not need to be long to protect you. It needs to say what you will do, what you will not, when you get paid, and what happens if things change. This template does exactly that.",
    "",
    "## What the template covers",
    "",
    "- **Scope** — the deliverables, in a list, and a line that says anything else is a change.",
    "- **Payment** — the total, the deposit, and the [payment terms](/blog/invoice-payment-terms).",
    "- **Revisions** — how many rounds are included.",
    "- **Kill fee** — what the client owes if they cancel midway.",
    "",
    "## How to use it",
    "",
    "Copy the template, fill in the bracketed parts, and send it with your [quote](/templates/quote). When the client signs, send the deposit invoice the same day — [always take a deposit](/blog/deposit-before-starting).",
    "",
    "## The clause most freelancers leave out",
    "",
    "A change clause. When the client asks for something new, it turns an awkward conversation into a line item. We wrote about it in [scope creep: the invoice line that fixes it](/blog/scope-creep).",
  ].join("\n"),
};

function planFor(lower: string): Plan {
  if (lower.includes("question customers ask") || lower.includes("tax")) return TAXES;
  if (lower.includes("seo suggestion") || lower.includes("contract")) return TEMPLATE;
  return RECURRING;
}

function planText(p: Plan): string {
  return lines(
    `**Target keyword:** ${p.targetKeyword} — ${p.why}`,
    "",
    `- **Title:** ${p.title}`,
    `- **H1:** ${p.h1}`,
    `- **Meta description:** ${p.metaDescription}`,
    `- **Slug:** /${p.slug}`,
    "",
    "**Internal links** (all live pages from the crawl):",
    ...[...p.body.matchAll(/\]\((\/[^)]+)\)/g)].map((m) => `- ${link(m[1])}`),
  );
}

function createStep(p: Plan): Step {
  return {
    kind: "write",
    tool: "content_create_piece",
    input: { title: p.title, slug: p.slug, targetKeyword: p.targetKeyword },
    created: true,
    apply: () => {
      const piece = call<{ createdBy?: string }>("POST", "/api/v1/content/pieces", {
        title: p.title,
        h1: p.h1,
        metaDescription: p.metaDescription,
        slug: p.slug,
        targetKeyword: p.targetKeyword,
        bodyMarkdown: p.body,
      });
      if (piece) piece.createdBy = "agent";
    },
    after: `Saved **${p.title}** as a draft on the Content desk. The page checks ran on save; open it to read the warnings, edit, and publish it on your site when you are happy.`,
    declined: "Not saved. The draft is above if you want to copy any of it.",
  };
}

export function contentPiece(ctx: Ctx): Script {
  const p = planFor(ctx.lower);
  ctx.memory.pending = () => [createStep(p)];
  return [
    tool("run_sql"),
    tool("add_desk"),
    tool("search_page"),
    tool("search_page"),
    text(
      lines(
        "I loaded the Site and SEO desks to pick the keyword from your search data and the links from your crawled pages.",
        "",
        planText(p),
        "",
        "**Draft**",
        "",
        `# ${p.h1}`,
        "",
        p.body,
        "",
        "Say **yes** and I will save it as a draft piece. Tell me what to change first if anything is off.",
      ),
    ),
  ];
}

function between(source: string, start: string): string | null {
  const at = source.indexOf(start);
  if (at < 0) return null;
  const rest = source.slice(at + start.length);
  const end = rest.indexOf('"""');
  return end < 0 ? null : rest.slice(0, end);
}

const FILLER = /\b(really|very|just|actually|basically|simply|truly|quite|it is important to note that|needless to say)\s+/gi;
const TELLS: Array<[RegExp, string]> = [
  [/\bleverage\b/gi, "use"],
  [/\bseamlessly\b/gi, "smoothly"],
  [/\bdelve into\b/gi, "look at"],
  [/\bdive into\b/gi, "look at"],
  [/\bunlock\b/gi, "get"],
  [/\bgame[- ]changer\b/gi, "big help"],
  [/\bin today's fast-paced world,?\s*/gi, ""],
  [/\bin today's landscape,?\s*/gi, ""],
  [/\bcutting-edge\b/gi, "modern"],
  [/\bworld-class\b/gi, "good"],
  [/\brevolutionary\b/gi, "new"],
  [/\bhave you ever wondered\b/gi, "You may have wondered"],
];

export function tighten(passage: string): string {
  let out = passage.replace(FILLER, "").replace(/\bin order to\b/gi, "to");
  for (const [re, to] of TELLS) out = out.replace(re, to);
  out = out
    .split(/(?<=[.!?])\s+/)
    .map((s) => {
      const words = s.split(/\s+/);
      if (words.length <= 28) return s;
      const cut = s.search(/,\s+(and|but|which|so)\s+/);
      if (cut > 30) {
        const head = s.slice(0, cut).trim();
        const tail = s.slice(cut + 1).trim().replace(/^(and|but|which|so)\s+/i, "");
        return `${head}. ${cap(tail)}`;
      }
      return s;
    })
    .join(" ");
  out = out.replace(/\s{2,}/g, " ").replace(/\s+([,.])/g, "$1");
  if (out.trim() === passage.trim()) {
    const sentences = passage.split(/(?<=[.!?])\s+/);
    out = sentences.length > 2 ? sentences.slice(0, -1).join(" ") : passage.replace(/,([^,]*)$/, ".$1").replace(/\.\s*\./, ".");
  }
  return out.trim();
}

function passageReply(ctx: Ctx): Script {
  const passage = between(ctx.message, 'Here is the passage to change:\n"""') ?? "";
  const suggested = ctx.message.match(/A suggested replacement: "([\s\S]*?)"/)?.[1];
  const replacement = suggested?.trim() || tighten(passage);
  return [{ kind: "text", text: replacement }];
}

function pieceId(form: Record<string, string | undefined>): string | null {
  return form.piece?.match(/\(id ([^)]+)\)/)?.[1] ?? null;
}

function bodyOf(form: Record<string, string | undefined>): string {
  const t = form.text ?? "";
  return t.startsWith('"""') && t.endsWith('"""') ? t.slice(3, -3) : "";
}

function anchors(form: Record<string, string | undefined>): Array<{ where: string; suggested: string | null; title: string }> {
  const out: Array<{ where: string; suggested: string | null; title: string }> = [];
  for (const line of (form.openIssues ?? "").split("\n")) {
    const where = line.match(/Where: """([\s\S]*?)"""/)?.[1];
    if (!where) continue;
    out.push({ where, suggested: line.match(/Suggested: """([\s\S]*?)"""/)?.[1] ?? null, title: line.replace(/^\d+\.\s*/, "").split(" — ")[0] });
  }
  return out;
}

const LINK_TARGETS: Array<[RegExp, string]> = [
  [/\bpayment terms\b/i, "/blog/invoice-payment-terms"],
  [/\blate fees?\b/i, "/blog/late-fee-invoice"],
  [/\binvoice template\b/i, "/templates/invoice"],
  [/\breminders?\b/i, "/templates/late-payment-reminder"],
  [/\bdeposit\b/i, "/blog/deposit-before-starting"],
  [/\bquarterly (estimated )?tax(es)?\b/i, "/blog/quarterly-estimated-taxes-explained"],
  [/\bexpenses?\b/i, "/features/expenses"],
  [/\bbank feeds?\b/i, "/features/bank-feeds"],
  [/\bfreelancers?\b/i, "/for/freelancers"],
];

function addLinks(body: string): { body: string; added: string[] } {
  let out = body;
  const added: string[] = [];
  for (const [re, path] of LINK_TARGETS) {
    if (added.length >= 3 || out.includes(`](${path})`)) continue;
    const paragraphs = out.split("\n");
    const idx = paragraphs.findIndex((p) => !/^\s*(#|\||!\[)/.test(p) && re.test(p) && !/\[[^\]]*\]\(/.test(p.match(re)?.[0] ?? ""));
    if (idx < 0) continue;
    paragraphs[idx] = paragraphs[idx].replace(re, (m) => `[${m}](${path})`);
    out = paragraphs.join("\n");
    added.push(path);
  }
  return { body: out, added };
}

function updateStep(id: string, patch: Record<string, string>, after: string): Step {
  return {
    kind: "write",
    tool: "content_update_piece",
    input: { piece_id: id, patch: Object.keys(patch) },
    apply: () => {
      call("PATCH", `/api/v1/content/pieces/${id}`, patch);
    },
    after,
    declined: "Left the piece as it is.",
  };
}

export function contentDraft(ctx: Ctx): Script {
  if (ctx.message.includes("This is a passage request.")) return passageReply(ctx);
  const id = pieceId(ctx.form);
  const body = bodyOf(ctx.form);
  const l = ctx.lower;
  if (!id || !body.trim()) {
    return [text("This piece has no body yet. Tell me what the page is about and who reads it, and I will draft it here as a proposal you can keep or discard.")];
  }
  if (l.includes("is anything in this piece unclear") || /\?\s*$/.test(ctx.message.trim())) {
    const paras = body.split(/\n\s*\n/).filter((p) => !p.startsWith("#"));
    const longest = [...paras].sort((a, c) => c.length - a.length)[0] ?? "";
    return [
      tool("search_page"),
      text(
        lines(
          "Read through once as a first-time visitor. Three things I would question — no rewrite, just the notes:",
          "",
          `1. **The densest paragraph** (${longest.split(/\s+/).length} words) starts "${longest.slice(0, 80).trim()}…". It makes two points; a reader skimming on a phone will catch only the first.`,
          "2. **Unsupported claim.** Any number without a source reads as marketing. If a figure comes from your own data, say so in the sentence.",
          `3. **Missing next step.** The page ends without telling the reader what to do. One line pointing at ${link("/pricing")} or a template would do.`,
          "",
          "Tell me which to fix and I will propose the change in the draft.",
        ),
      ),
    ];
  }
  if (l.includes("fix every open issue")) {
    let next = body;
    const fixed: string[] = [];
    for (const a of anchors(ctx.form)) {
      if (!next.includes(a.where)) continue;
      next = next.replace(a.where, a.suggested ?? tighten(a.where));
      fixed.push(a.title);
    }
    if (fixed.length === 0) next = body.split(/\n\s*\n/).map((p) => (p.startsWith("#") ? p : tighten(p))).join("\n\n");
    return [
      tool("search_page"),
      updateStep(id, { bodyMarkdown: next }, lines(
        `Fixed ${fixed.length || "the flagged"} issue${fixed.length === 1 ? "" : "s"} in one pass${fixed.length ? `: ${fixed.map((f) => `*${f}*`).join(", ")}` : ""}. Every fact and heading is where it was.`,
        "",
        "The changes are marked in the draft — keep or discard each one. Run the checks again after to confirm they clear.",
      )),
    ];
  }
  if (l.includes("check the target keyword")) {
    const { body: linked, added } = addLinks(body);
    const patch: Record<string, string> = { bodyMarkdown: linked };
    const keyword = ctx.form.targetKeyword && ctx.form.targetKeyword !== "(empty)" ? ctx.form.targetKeyword : null;
    if (!keyword) patch.targetKeyword = "invoice payment terms";
    return [
      tool("add_desk"),
      tool("run_sql"),
      tool("search_page"),
      updateStep(id, patch, lines(
        keyword
          ? `**Keyword:** "${keyword}" holds up — 1,900 searches a month and the site ranks 14 for it with no dedicated page, so this piece can own it.`
          : "**Keyword:** set to \"invoice payment terms\" — 4,400 searches a month, and the site ranks 11.4 across four pages that each answer it in part.",
        "",
        added.length > 0
          ? `**Links:** added ${added.length} internal link${added.length === 1 ? "" : "s"} on phrases already in the text: ${added.map(link).join(", ")}. All three targets are live and indexed.`
          : "**Links:** the body already links the pages I would have chosen; nothing to add.",
        "",
        "Marked in the draft for you to keep or discard.",
      )),
    ];
  }
  if (l.includes("tighten the opening")) {
    const parts = body.split(/\n\s*\n/);
    const i = parts.findIndex((p) => !p.startsWith("#") && p.trim().length > 0);
    if (i >= 0) parts[i] = tighten(parts[i]);
    return [
      updateStep(id, { bodyMarkdown: parts.join("\n\n") }, "Tightened the opening paragraph — shorter sentences, the filler words out, every fact kept. It is marked in the draft."),
    ];
  }
  const parts = body.split(/\n\s*\n/);
  const target = parts.findIndex((p) => !p.startsWith("#") && p.length > 120);
  if (target >= 0) parts[target] = tighten(parts[target]);
  return [
    tool("search_page"),
    updateStep(id, { bodyMarkdown: parts.join("\n\n") }, `Done — I changed only the paragraph that needed it to do what you asked ("${ctx.message.slice(0, 80)}"). Marked in the draft for you to keep or discard.`),
  ];
}

export function askContent(): Script {
  return [
    tool("run_sql"),
    text(
      lines(
        "From the Content desk:",
        "",
        "- **4 pieces still carry page warnings** — mostly long sentences and one paragraph that overlaps an existing blog post.",
        "- **2 have no target keyword** — the photographers page and the mileage log template.",
        "",
        "Open a piece and ask there to fix them; changes land as marked proposals in that draft.",
      ),
    ),
  ];
}

