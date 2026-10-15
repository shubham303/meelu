import type { SocialListeningPost } from "@demo/lib/types";
import { callPaged } from "../hooks";
import { lines, text, tool, type Ctx, type Script } from "./common";

const PLATFORM: Record<string, string> = { reddit: "Reddit", hackernews: "Hacker News", x: "X", linkedin: "LinkedIn", bluesky: "Bluesky" };

function toReply(): SocialListeningPost[] {
  return callPaged<SocialListeningPost>("/api/v1/social-listening/posts?status=to_reply&page=1&page_size=50");
}

function rank(posts: SocialListeningPost[]): SocialListeningPost[] {
  const score = (p: SocialListeningPost) =>
    (p.similarity ?? 0.5) * 100 + Math.min(40, (p.engagement?.comments ?? 0) / 2) - (p.postedAt ? (Date.now() - Date.parse(p.postedAt)) / 3_600_000 / 6 : 0);
  return [...posts].sort((a, c) => score(c) - score(a));
}

export function askSocial(ctx: Ctx): Script {
  const posts = rank(toReply());
  if (posts.length === 0) {
    return [
      tool("run_sql"),
      text("There is nothing waiting for a reply right now. Press **Run now** on the Social Listening screen to look again; posts already shown never come back."),
    ];
  }
  const top = posts.slice(0, 3);
  const skip = posts.slice(-1)[0];
  const l = ctx.lower;
  if (l.includes("keeps nothing") || l.includes("line")) {
    return [
      tool("run_sql"),
      text(
        lines(
          "Looking at the last run line by line: the lines phrased like a question a freelancer would actually type (\"which app do you use to invoice clients\") keep posts; the ones phrased like a product description (\"bookkeeping software for small teams\") match marketing posts and get judged out.",
          "",
          "If a line keeps nothing, rewrite it as the sentence someone with the problem would post. You decide the wording — I can save new lines once you agree.",
        ),
      ),
    ];
  }
  return [
    tool("run_sql"),
    text(
      lines(
        `${posts.length} posts are waiting. The three I would answer first:`,
        "",
        ...top.map((p, i) =>
          lines(
            `${i + 1}. **${p.title ?? (p.text ?? "").slice(0, 80)}** — ${PLATFORM[p.platform] ?? p.platform}${p.context?.subreddit ? `, r/${p.context.subreddit}` : ""}${p.engagement?.comments ? `, ${p.engagement.comments} comments` : ""}`,
            `   - Why: ${p.keepReason ?? "the poster is choosing a tool right now"}`,
            `   - Angle: ${p.suggestedAngle ?? "answer the question first; mention Ledgerly only if it fits"}`,
          ),
        ),
        "",
        skip && !top.includes(skip) ? `Lowest priority: "${skip.title ?? (skip.text ?? "").slice(0, 60)}" — older and only loosely about bookkeeping.` : "",
        "",
        "Open a post to draft the reply; you send it yourself.",
      ),
    ),
  ];
}

function field(message: string, label: string): string {
  return message.match(new RegExp(`^${label}: (.*)$`, "m"))?.[1]?.trim() ?? "";
}

export function composeReply(ctx: Ctx): Script {
  const m = ctx.message;
  const title = field(m, "Title");
  const body = field(m, "Text");
  const request = field(m, "Request").toLowerCase();
  const draft = m.match(/My current draft:\n([\s\S]*?)\n\nRequest:/)?.[1]?.trim() ?? "";
  const topic = `${title} ${body}`.toLowerCase();

  let reply: string;
  if (/tax|quarterly|estimated|1099/.test(topic)) {
    reply =
      "What worked for me: move 25–30% of every payment into a separate account the day it lands, then check the real number once a quarter against last year's effective rate. The quarterly payment stops being a surprise. Most bookkeeping tools (Ledgerly included — I work there) will estimate it for you, but the separate account is the part that actually saves you.";
  } else if (/late|overdue|chase|paid|payment/.test(topic)) {
    reply =
      "Two things that cut my late payments roughly in half: put the due date as a date, not \"net 30\", and send a short, friendly reminder three days after it passes — automated, so you never have to decide whether to chase. If it is still unpaid at 30 days, a late fee clause you agreed upfront makes the second email much easier to write.";
  } else if (/quickbooks|freshbooks|wave|xero|switch|alternative|app|software|tool/.test(topic)) {
    reply =
      "Depends on what you bill. If it is mostly invoices and expenses for one person, you do not need QuickBooks — it is built for accountants. I work on Ledgerly, so I am biased, but whatever you pick, check two things: whether it imports your bank transactions without a paid add-on, and whether your accountant can export from it in one click.";
  } else {
    reply =
      "Good question. The simplest version that holds up: one business account, every receipt attached to the transaction when it happens, and ten minutes a week to categorise. Anything fancier is optional. (I work on a bookkeeping app, Ledgerly, so take the tool advice with salt — the habit matters more than the tool.)";
  }
  if (draft && /shorter|tighten|trim|concise/.test(request)) reply = draft.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ");
  else if (draft && /less salesy|no pitch|don't mention|without mentioning|remove.*(ledgerly|plug)/.test(request))
    reply = (draft || reply).replace(/\s*\(?I work (on|at) [^.)]*[.)]\)?/gi, "").replace(/\s*\(?Ledgerly[^.)]*[.)]\)?/gi, "").trim();
  else if (/shorter|tighten|trim|concise/.test(request)) reply = reply.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ");
  else if (/less salesy|no pitch|don't mention|without mentioning/.test(request))
    reply = reply.replace(/\s*\(?I work (on|at) [^.)]*[.)]\)?/gi, "").replace(/\s*\(?Ledgerly[^,.)]*[,.)]\)?/gi, "").trim();
  else if (/friendl|warmer|casual/.test(request)) reply = `Been there! ${reply}`;
  else if (/formal|professional/.test(request)) reply = reply.replace(/^Good question\. /, "").replace(/!/g, ".");
  return [{ kind: "text", text: reply }];
}
