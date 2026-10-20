import type { Lead, LeadBrief } from "@demo/lib/types";
import { call, callPaged } from "../hooks";
import { lines, text, tool, type Ctx, type Script, type Step } from "./common";

const SUGGESTED = [
  "Freelancers who just left an agency job and are sending their first invoices",
  "Small design studios (2–10 people) that say their invoicing tool got too expensive",
];

function briefs(): LeadBrief[] {
  return call<LeadBrief[]>("GET", "/api/v1/find-leads/briefs") ?? [];
}

function newLeads(): Lead[] {
  return callPaged<Lead>("/api/v1/find-leads/leads?status=new&page=1&page_size=50");
}

function saveStep(texts: string[]): Step {
  return {
    kind: "write",
    tool: "find_leads_save_briefs",
    input: { briefs: texts },
    apply: () => {
      for (const t of texts) call("POST", "/api/v1/find-leads/briefs", { text: t, sources: ["posts", "linkedin"] });
    },
    after: `Saved ${texts.length} briefs. Press **Find leads** when you are ready; nothing searches until you do.`,
    declined: "Nothing saved. Tell me how to reword them.",
  };
}

export function leadsSetup(ctx: Ctx): Script {
  ctx.memory.pending = () => [saveStep(SUGGESTED)];
  const have = briefs();
  return [
    tool("run_sql"),
    tool("search_page"),
    text(
      lines(
        `I read the site record, the profile and the ${have.length} briefs you already have. Ledgerly sells to one-person businesses who invoice clients, so two groups are missing:`,
        "",
        ...SUGGESTED.map((t, i) => `${i + 1}. ${t}`),
        "",
        "The first is the moment people pick their first tool. The second is a pricing complaint your /pricing page answers directly.",
        "",
        "Say **yes** to save both, or tell me what to change.",
      ),
    ),
  ];
}

export function askLeads(ctx: Ctx): Script {
  const l = ctx.lower;
  const leads = newLeads();
  if (/keeps nobody|kept nobody|no one|nobody/.test(l)) {
    return [
      tool("run_sql"),
      text(
        lines(
          "The accountants brief is switched off, so it kept nobody in the last run. Before you turn it back on: LinkedIn found 58 profiles for it last time, but only 6 passed the check, because most accountants post about tax deadlines, not about recommending software.",
          "",
          "A sharper wording would be *Accountants who post about onboarding freelance clients*. I can reword it once you agree.",
        ),
      ),
    ];
  }
  if (/what to say|what should i say|reach out|opening|write to/.test(l)) {
    const lead = leads[0];
    if (!lead) return [text("There is nobody new on the list right now.")];
    return [
      tool("run_sql"),
      text(
        lines(
          `For **${lead.name}**, start from what they wrote: "${lead.evidence[0]?.quote ?? lead.snippet}"`,
          "",
          `Opening: ${lead.angle}`,
          "",
          "Keep it to the opening line and a question; write the rest in your own words. If you email them, I can load the Email desk and save it as a draft in your Gmail — you send it.",
        ),
      ),
    ];
  }
  const top = leads.slice(0, 3);
  return [
    tool("run_sql"),
    text(
      lines(
        `${leads.length} people are waiting. The three most worth a message today:`,
        "",
        ...top.map((p, i) => `${i + 1}. **${p.name}** (${p.headline ?? p.platform}) — ${p.reason}`),
        "",
        "Open a card for the evidence and a link to reach them. When you have written to someone, mark them contacted.",
      ),
    ),
  ];
}

export function leadsAnswer(ctx: Ctx): Script {
  return ctx.action === "find-leads-setup" ? leadsSetup(ctx) : askLeads(ctx);
}
