import { analyticsAnswer } from "./analytics";
import { lines, link, text, tool, type Ctx, type Script } from "./common";
import { contentPiece } from "./content";
import { askSocial } from "./social";

function splitQueries(): Script {
  return [
    tool("run_sql"),
    tool("run_sql"),
    text(
      lines(
        "Three search queries are split between two or more of your pages in the last 28 days of Search Console:",
        "",
        `1. **"freelance invoice template"** — ${link("/templates/invoice")} (avg. position 6.8) and ${link("/tools/invoice-generator")} (9.4) both get impressions. The template page has the downloadable files; the generator fills them in online.`,
        `2. **"quickbooks alternative"** — ${link("/compare/quickbooks")} (7.2) and ${link("/blog/quickbooks-alternatives")} (11.4). The compare page is one-to-one; the blog post lists six tools.`,
        `3. **"late payment reminder email"** — ${link("/templates/late-payment-reminder")} (7.7) and ${link("/blog/late-paying-clients")} (8.9). One has the wording, the other the timeline.`,
        "",
        "For the first, a pillar page on invoicing as a freelancer that links down to both would let each keep its own job. For the others, a clear link between the pair may be enough.",
        "",
        "These are suggestions: whether to refocus, merge or leave a page is your call. The Site desk can turn any of them into link or pillar suggestions you approve one by one.",
      ),
    ),
  ];
}

export function overviewAnswer(ctx: Ctx): Script {
  const l = ctx.lower;
  if (/compete|split/.test(l)) return splitQueries();
  if (/conversation|social/.test(l)) return [tool("add_desk"), ...askSocial(ctx)];
  if (/draft|new page|keyword worth/.test(l)) return contentPiece(ctx);
  if (/changed|search console|clicks/.test(l)) return [tool("add_desk"), ...analyticsAnswer({ ...ctx, lower: "what changed in clicks" })];
  return [
    tool("run_sql"),
    text(
      lines(
        "From the overview I can see your pages, the last crawl, Search Console and Analytics totals and your notes. For anything deeper I load the desk that owns it — SEO, Content, Social Listening, Find Leads, GEO or Analytics — in the same reply.",
        "",
        "This is the demo, so full answers are prepared for the chips. Try one of them.",
      ),
    ),
  ];
}
