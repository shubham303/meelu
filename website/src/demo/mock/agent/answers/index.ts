import { analyticsAnswer } from "./analytics";
import { isNo, isYes, lines, text, tool, type Ctx, type Script } from "./common";
import { askContent, contentDraft, contentPiece } from "./content";
import { profileAnswer } from "./profile";
import { seoAnswer } from "./seo";
import { pagesFallback, siteAnswer } from "./site";
import { askSocial, composeReply } from "./social";

export type { Ctx, Memory, Script, Step } from "./common";

const CHIP_LENGTH = 160;

function fallback(ctx: Ctx): Script {
  const asked = ctx.message.length > 140 ? `${ctx.message.slice(0, 137).trimEnd()}…` : ctx.message;
  const where: Record<string, string> = {
    "ask-site": "the website record, the crawl and the technical audit",
    "ask-seo": "Search Console, Analytics and the saved SEO lists",
    "issue-review": "the open technical checks and the pages they flag",
    plan: "every desk's tables",
  };
  return [
    tool("run_sql"),
    tool("search_page"),
    text(
      lines(
        `I read ${where[ctx.action] ?? "what this desk holds"} for ledgerly.app before answering "${asked}".`,
        "",
        "This is the demo, so the answers are prepared for the chips above rather than written live. In the Meelu app this turn runs on your machine against your own data, reads everything the desk is scoped to, and can only write with the tools listed at the top of this panel — and it asks before every write.",
        "",
        "Try one of the suggestions to see a full answer, with the evidence behind it.",
      ),
    ),
  ];
}

function byAction(ctx: Ctx): Script {
  switch (ctx.action) {
    case "ask-site":
    case "issue-review":
      return siteAnswer(ctx) ?? fallback(ctx);
    case "ask-pages":
      return siteAnswer(ctx) ?? pagesFallback(ctx);
    case "ask-seo":
      return seoAnswer(ctx) ?? fallback(ctx);
    case "content-piece":
      return contentPiece(ctx);
    case "content-draft":
      return contentDraft(ctx);
    case "ask-content":
      return askContent();
    case "profile-setup":
      return profileAnswer(ctx);
    case "ask-analytics":
      return analyticsAnswer(ctx);
    case "ask-social-listening":
    case "social-listening-setup":
      return askSocial(ctx);
    case "compose-reply":
      return composeReply(ctx);
    default:
      return siteAnswer(ctx) ?? seoAnswer(ctx) ?? fallback(ctx);
  }
}

export function answer(ctx: Ctx): Script {
  const m = ctx.memory;
  const pending = m.pending;
  const awaiting = m.awaiting;
  m.pending = null;
  m.awaiting = null;
  if (pending) {
    if (isYes(ctx.lower)) return pending(ctx);
    if (isNo(ctx.lower)) return [text("Fine — nothing saved. Tell me what to change, or ask something else.")];
  }
  if (awaiting && ctx.message.length < CHIP_LENGTH) return awaiting(ctx);
  return byAction(ctx);
}
