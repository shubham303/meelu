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
    key: "outreach",
    name: "Outreach",
    href: "/dashboard/outreach",
    icon: "send",
    tagline: "Finds people worth writing to, and writes the first email.",
    summary:
      "You describe who you want to reach and why they'd care. Your coworker goes and finds " +
      "them — with the evidence for why each one fits — and drafts an individual email to each, " +
      "argued from your website's positioning rather than a template. Every draft waits for " +
      "your yes, and then goes out through the email server you've installed beside Meelu — or " +
      "from your own client if you'd rather.",
    chain: [
      { label: "Project", sub: "the standing brief" },
      { label: "Campaign", sub: "one run of it" },
      { label: "Prospect", sub: "a lead, with evidence" },
      { label: "Email", sub: "what you'd send" },
    ],
    chainNote:
      "A project is reused across runs. When a campaign starts, the brief is frozen onto it — " +
      "so months later you can still see the exact instructions that produced that campaign's " +
      "output, even though you have edited the project six times since.",
    prompts: [
      {
        say: "Set up an outreach project for [who you want to reach]. What we offer them is [value], and I want to ask them for [the ask].",
        then: "A project you can reuse — the brief every future campaign is argued from.",
      },
      {
        say: "Start a campaign on that project and find 20 prospects. Tell me why each one fits before you save them.",
        then: "Prospects land on the campaign, each with a fit reason and the URL it came from.",
      },
      {
        say: "Draft emails for the new prospects. Read my writing voice first and keep them short.",
        then: "One draft per prospect, in your voice, sitting as `draft`.",
      },
      {
        say: "Read the drafts back to me. If they're good, send them and mark them sent.",
        then: "They go out through the email connection in the Meelu app; each one is recorded sent, or failed with the provider's error.",
      },
      {
        say: "I sent the one to [name] myself — mark it sent. The one to [name] bounced.",
        then: "Statuses move to sent and failed. Those three states are the whole lifecycle, however it went out.",
      },
    ],
    rules: [
      {
        title: "A prospect belongs to a project, not a campaign",
        detail:
          "Two campaigns under one project can never hold the same lead. Without that, your " +
          "second run re-finds the same newsletters and someone gets two cold emails from you " +
          "about the same thing — the exact failure that makes outreach feel like spam. It is " +
          "enforced three times over: an exclusion list the agent loads before searching, a " +
          "uniqueness check on write, and identity matching on email → domain → company, so the " +
          "same organisation reached through a different person still counts as a duplicate.",
      },
      {
        title: "Different projects may overlap freely",
        detail:
          "Those are different conversations with different value propositions, so reaching the " +
          "same company under two of them is legitimate rather than a mistake.",
      },
      {
        title: "Meelu is the memory; the sending is a connection's job",
        detail:
          "Meelu holds the brief, the leads, the drafts and the record of what happened, and it " +
          "carries no mail transport of its own — on purpose. Connect an email account in the " +
          "Meelu app and your coworker sends the draft it just wrote, in the same conversation, " +
          "then records the outcome here. With nothing connected the draft simply waits for " +
          "your own client.",
      },
    ],
    limits: [
      "Nothing goes out without your yes on the exact text — being able to send is precisely " +
        "what makes that approval the thing that matters, not a formality.",
      "It marks an email sent only when a send actually happened: the send tool succeeded, or " +
        "you said you sent it. Never because a draft looked ready — the record and your outbox " +
        "are not allowed to disagree.",
      "It won't invent a proof point. Numbers and customer names come off your website record, " +
        "or they don't appear.",
    ],
    tools: "outreach_*",
  },
  {
    key: "content",
    name: "Content",
    href: "/dashboard/content",
    icon: "calendar",
    tagline: "Writes each piece for the one place it goes.",
    summary:
      "A piece is one thing written for one channel — a page for the website, a LinkedIn post, " +
      "an Instagram caption. You pick the channel when you start it, and your coworker drafts " +
      "against that channel's own rules, into a calendar that already knows your timezone and " +
      "the gap you keep between posts. The same idea for another channel is a clone, rewritten.",
    chain: [
      { label: "Channel", sub: "the site's rules for it" },
      { label: "Piece", sub: "one thing written, for that channel" },
      { label: "Slot", sub: "when it goes out" },
    ],
    chainNote:
      "A piece is published from its own editor. The list says exactly where each one stands: " +
      "draft, scheduled, posted, failed, or blocked by the channel's limits.",
    prompts: [
      {
        say: "Write a LinkedIn post about the grinder launch.",
        then: "One piece in draft, written to LinkedIn's rules and checked against its limits.",
      },
      {
        say: "Fill next week from what we've been working on.",
        then: "Pieces land in free slots, one per channel, never two in the same hour.",
      },
      {
        say: "Move Thursday's LinkedIn post to Friday morning.",
        then: "Rescheduled — refused if it would land on top of another post on that channel.",
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
      {
        title: "A slot holds one post per channel",
        detail:
          "The spacing you set is enforced on write, which is what stops a productive afternoon " +
          "becoming four posts in one hour.",
      },
    ],
    limits: [
      "Meelu publishes to social through managed publishing once an account is connected; " +
        "where it isn't, you paste the piece in yourself. The website is always yours to " +
        "publish — record the URL when it's live.",
      "Marking a piece posted is yours, and the server enforces it. Only the person " +
        "looking at the channel knows it really went up.",
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
