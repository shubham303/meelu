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
    tagline: "Writes pages for your website, ready to publish.",
    summary:
      "A piece is one web page for your site: SEO title, H1, meta description, slug, target " +
      "keyword and body. Before it writes, your coworker loads your Site and SEO data to pick " +
      "the keyword the page should win and the internal links it should carry.",
    chain: [
      { label: "Research", sub: "keyword from search data, links from the crawl" },
      { label: "Piece", sub: "one web page, every field filled" },
      { label: "Publish it", sub: "you, on your site" },
    ],
    chainNote:
      "Meelu keeps the page and checks it on every save: title length, meta description, H1, " +
      "keyword placement. Publishing is yours.",
    prompts: [
      {
        say: "Write a page on how to pick an espresso grinder.",
        then: "A keyword proposed from your search data, links to real pages, then a full draft to approve.",
      },
      {
        say: "Write the page the SEO desk suggested adding.",
        then: "The page, built from that suggestion's brief and keywords.",
      },
      {
        say: "Add better internal links to this piece.",
        then: "Links to crawled pages that fit, proposed as marked changes you keep or discard.",
      },
    ],
    rules: [
      {
        title: "Grounded in your own data",
        detail:
          "The target keyword comes from your keywords and Search Console queries, and every " +
          "internal link points at a page the crawl found. Nothing is invented.",
      },
      {
        title: "One query, one page",
        detail:
          "If a page on your site already ranks for the keyword, Meelu says so and suggests " +
          "editing that page instead of writing a second one.",
      },
    ],
    limits: [
      "Meelu never publishes. Copy the markdown out and put it on your site yourself.",
      "Meelu writes web pages only. It does not write or schedule social posts.",
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
