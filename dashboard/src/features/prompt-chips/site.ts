import type { PromptChip } from "./lib";

const PROFILE: PromptChip = {
  label: "Build site profile",
  prompt: [
    "Write down what this business actually is, from what its pages say.",
    "Search what has been crawled rather than walking the whole site, and open the pages that decide it — home, product, pricing, about.",
    "Say what the site covers well, what it covers thinly, and what it never mentions.",
    "Do not write about products or prices no page states. Where the evidence is thin, say so.",
    "Save the summary once I have agreed to it.",
  ].join(" "),
};

const GAPS: PromptChip = {
  label: "What does this site not cover?",
  prompt: [
    "Search what has been read of this site and tell me the gaps.",
    "Name topics a visitor would expect and find nothing on, and quote the passage that came closest for each.",
    "Say plainly where the crawl is incomplete rather than calling a hole a gap.",
  ].join(" "),
};

const BROKEN: PromptChip = {
  label: "What is broken on the site?",
  prompt: [
    "Read the crawl status and tell me what is actually wrong with this site.",
    "Separate pages that returned 404 or 410 from pages that refused us with a 403 or failed to respond — those are different problems.",
    "For anything broken, say which pages link to it, so there is something to fix.",
  ].join(" "),
};

const SITEMAP: PromptChip = {
  label: "What is missing from the sitemap?",
  prompt: [
    "Tell me which pages the crawl found by following links that the sitemap does not list, and which sitemap URLs are dead.",
    "Say which of the unlisted pages look worth listing and which look like they should not be indexed at all.",
  ].join(" "),
};

const THIN: PromptChip = {
  label: "Which pages are thin?",
  prompt: [
    "Tell me which of the pages that have been read carry almost nothing — little text, no real answer on them.",
    "Read the handful that matter rather than every one, and for each say whether it should be written out, merged into a page that already covers it, or dropped.",
  ].join(" "),
};

const DUPLICATES: PromptChip = {
  label: "Is this already covered?",
  prompt: [
    "I will name a topic. Search what the site already says about it and tell me whether it is covered, half covered, or absent.",
    "Quote the closest passages and link the pages they sit on, so I can judge whether a new page would duplicate one I have.",
  ].join(" "),
};

const CHANGED: PromptChip = {
  label: "What changed in the last 90 days?",
  prompt: [
    "Read the measured search data and tell me what actually changed in the last 90 days — the pages and queries that gained or lost the most, with positions.",
    "Every number should be measured, from Search Console; say plainly if the site has too few impressions for any of it to mean much.",
    "For the biggest losers, read the page and offer one sentence on the likeliest reason.",
  ].join(" "),
};

const STRIKING: PromptChip = {
  label: "What is close to the top ten?",
  prompt: [
    "Read the striking-distance list — the queries where this site already ranks 8 to 15 with real impressions.",
    "For each of the top few, use the inlink count the list carries to say whether the owning page needs links (it has almost none) or content (it is already well linked).",
    "Positions are measured; do not pad the list with keywords the site does not rank for.",
  ].join(" "),
};

const DROPPED: PromptChip = {
  label: "Why did this page drop?",
  prompt: [
    "I will name a page. Read its measured search performance — the queries it receives, current window against the previous one — and its index status.",
    "Then read the page itself and say what the numbers can support: which queries it lost, whether the position or the click-through moved, and whether the index still has it at all.",
    "Say plainly what the data cannot tell you rather than inventing a cause.",
  ].join(" "),
};

const INVISIBLE: PromptChip = {
  label: "Where am I invisible?",
  prompt: [
    "Read the index status record and tell me which pages cannot perform at all because the index does not hold them.",
    "A page that is crawled but not indexed is Google declining the content — say so where the bucket is large, and say what that rules out.",
  ].join(" "),
};

export function desk(): PromptChip[] {
  return [PROFILE, CHANGED, GAPS, BROKEN];
}

export function search(): PromptChip[] {
  return [CHANGED, STRIKING, DROPPED, INVISIBLE];
}

export function traffic(): PromptChip[] {
  return [
    {
      label: "Where does my traffic come from?",
      prompt: [
        "Read the measured traffic and tell me where sessions actually come from — which channels and sources carry the site, and how the mix moved against the previous period.",
        "Say which movements are real and which are noise at this volume.",
      ].join(" "),
    },
    {
      label: "What actually converts?",
      prompt: [
        "Read the measured traffic and tell me which landing pages and channels produce key events, not just sessions.",
        "Name the pages that get traffic but convert nothing, and the ones that convert well but get little traffic.",
      ].join(" "),
    },
    {
      label: "What changed and why?",
      prompt: [
        "Compare this period's traffic against the previous one and explain the biggest movements — which channel, landing page or country drove each change.",
        "Distinguish a real shift from a one-day spike before drawing any conclusion.",
      ].join(" "),
    },
    {
      label: "Is organic pulling its weight?",
      prompt: [
        "Read the measured traffic and tell me what share Organic Search carries, how engaged those sessions are compared to other channels, and whether that share is growing.",
        "Cross-check against the search performance record where it sharpens the answer.",
      ].join(" "),
    },
  ];
}

export function pages(): PromptChip[] {
  return [DUPLICATES, GAPS, BROKEN, THIN];
}

export function technicalSeo(): PromptChip[] {
  return [
    {
      label: "What should I fix first?",
      prompt: [
        "Read the technical checks that are open on this website and tell me which ones are worth my time.",
        "Order them by what the problem actually costs this site, not by how many pages it touches, and name the pages behind each one.",
        "Say which are cosmetic so I can turn them down.",
      ].join(" "),
    },
    {
      label: "Explain this check",
      prompt: [
        "I will name one of the open checks. Explain what it is measuring, why it matters on a site like this one, and what a fix would look like on the pages it flagged.",
        "Read the pages it flagged before you answer — do not explain the check in the abstract.",
      ].join(" "),
    },
    {
      label: "What do crawlers miss without JavaScript?",
      prompt: [
        "Read the rendering findings on this website — the checks whose type is desktop or mobile, and the rendered-page records behind them for each device.",
        "Tell me which pages only show their content, links or tags after JavaScript runs, what differs between the desktop and the mobile render, what an AI crawler that never runs scripts actually sees, and whether the site as a whole depends on client-side rendering.",
        "If a device has not been rendered yet, say so and point me at the Desktop rendering or Mobile rendering tab on the Technical SEO screen.",
      ].join(" "),
    },
    BROKEN,
    SITEMAP,
  ];
}

