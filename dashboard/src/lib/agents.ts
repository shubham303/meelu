export type AgentGuideIcon =
  | "send"
  | "calendar"
  | "users"
  | "search"
  | "checklist"
  | "lightbulb"
  | "book";

export interface GuidePrompt {
  say: string;
  then: string;
}

export interface GuideRule {
  title: string;
  detail: string;
}

export interface AgentGuide {
  key: string;
  name: string;
  href: string | null;
  icon: AgentGuideIcon;
  tagline: string;
  summary: string;
  chain?: Array<{ label: string; sub: string }>;
  chainNote?: string;
  prompts: GuidePrompt[];
  rules: GuideRule[];
  limits: string[];
  tools: string;
}

export const AGENT_GUIDES: AgentGuide[] = [
  {
    key: "content",
    name: "Content",
    href: "/dashboard/content",
    icon: "calendar",
    tagline: "Writes each piece for the one place it goes.",
    summary:
      "A piece is one thing written for one channel — a page for the website, a LinkedIn post, " +
      "an Instagram caption. You pick the channel when you start it, and your coworker drafts " +
      "against that channel's own rules and hard limits. The same idea for another channel is " +
      "a clone, rewritten.",
    chain: [
      { label: "Channel", sub: "the site's rules for it" },
      { label: "Piece", sub: "one thing written, for that channel" },
      { label: "Post it", sub: "you, wherever it goes" },
    ],
    chainNote:
      "Meelu keeps the text and checks it. The list says where each piece stands: draft, or " +
      "blocked by the channel's limits. Posting is yours.",
    prompts: [
      {
        say: "Write a LinkedIn post about the grinder launch.",
        then: "One piece in draft, written to LinkedIn's rules and checked against its limits.",
      },
      {
        say: "Now do the same idea for X.",
        then: "A new piece cloned from the first, rewritten inside X's character limit.",
      },
      {
        say: "For LinkedIn specifically, stop opening posts with a question.",
        then: "The site's rules for that channel are edited — yours, not the shipped default.",
      },
    ],
    rules: [
      {
        title: "Each site owns its copy of the channel rules",
        detail:
          "Craft guidance ships with the product, is seeded onto the site once, and is yours from " +
          "that moment. A better default in a later release never rewrites what you have edited.",
      },
      {
        title: "Hard limits are checked, not suggested",
        detail:
          "Character counts, links, images — Meelu checks them on every save and blocks a piece " +
          "that breaks one. The rules the agent follows are prose; the limits are code.",
      },
    ],
    limits: [
      "Meelu never posts. Copy the piece out and publish it yourself, on the platform or " +
        "through whatever scheduler you already use. It sees what you wrote, not what went up.",
      "Instagram won't take a caption with no picture, so a piece without one stays blocked.",
    ],
    tools: "content_*",
  },
  {
    key: "site",
    name: "Site",
    href: "/dashboard/site",
    icon: "search",
    tagline: "Reads your whole website and remembers it, so everything after starts from what is actually there.",
    summary:
      "Your coworker reads every page your sitemap lists, from your own machine — one at a time, " +
      "so page three hundred is read as carefully as page one. What each page is, what it targets, " +
      "how you write. After that, \"is this covered?\" is a question with an answer.",
    prompts: [
      {
        say: "Read my website.",
        then: "Every page crawled, described and made searchable. Only what changed is re-read next time.",
      },
      {
        say: "Does anything on my site cover returns and refunds?",
        then: "The pages that do, and the exact passage that covers it — or a straight no, which is just as useful.",
      },
      {
        say: "What should I write next?",
        then: "Judged against what the site already covers, so you extend a gap instead of duplicating a page.",
      },
      {
        say: "Which of my pages are competing with each other?",
        then: "Pages chasing the same query — common, invisible without looking, and cheap to fix.",
      },
    ],
    rules: [
      {
        title: "It says when it is out of date",
        detail:
          "Every description records the version of the page it was written from. When a page " +
          "changes afterwards, the answer says so rather than quoting a description of a page " +
          "that no longer exists.",
      },
      {
        title: "Nothing modelled is presented as measured",
        detail:
          "This reads what your site says about itself. That is not what people search for, and " +
          "it is never reported as though it were.",
      },
    ],
    limits: [
      "The crawl runs on your machine, not ours — which is why it can read a staging site, and " +
        "why it needs the app open to run.",
      "It reads and remembers; it changes nothing. Editing a page or publishing a post is a " +
        "separate step with a separate server, after you say yes to that specific thing.",
      "Search is only as good as what has been read. A site indexed last month answers questions " +
        "about last month's site, and says so.",
    ],
    tools: "meelu_site_*",
  },
];

export function findAgentGuide(key: string): AgentGuide | undefined {
  return AGENT_GUIDES.find((g) => g.key === key);
}
