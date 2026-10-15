import type { PromptChip } from "./lib";

const CHANGED: PromptChip = {
  label: "What changed in the last 90 days?",
  blurb: "Pages and queries that gained or lost the most, measured.",
  prompt: [
    "Read the measured search data and tell me what actually changed in the last 90 days — the pages and queries that gained or lost the most, with positions.",
    "Every number should be measured, from Search Console; say plainly if the site has too few impressions for any of it to mean much.",
    "For the biggest losers, read the page and offer one sentence on the likeliest reason.",
  ].join(" "),
};

const STRIKING: PromptChip = {
  label: "What is close to the top ten?",
  blurb: "Search Console queries just off page one, where a push could get there.",
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

const TARGET_NEXT: PromptChip = {
  label: "What should I target next?",
  blurb: "Score the clusters and pick the few with the best odds and real demand.",
  prompt: [
    "Pick what this website should target next.",
    "Score the keyword clusters that have no score yet, starting with the ones people search most, then rank every scored cluster by winnability and then by monthly searches.",
    "Recommend the three to five best, and for each say why it is winnable, what kind of page would win it, and whether an existing page could own it instead of a new one.",
    "Treat each cluster as its main keyword; never recommend its other keywords as separate targets.",
  ].join(" "),
};

const BUILD_CLUSTERS: PromptChip = {
  label: "Build clusters for a topic",
  blurb: "Turn a few seed keywords into clusters, noise and off-topic searches removed.",
  prompt: [
    "I will name a topic. Choose a handful of seed keywords for it from what this website sells, show them to me, and once I agree build keyword clusters from them.",
    "When it is done, tell me how many clusters came out, how many keywords were dropped as noise or off-topic, and the biggest clusters by monthly searches.",
  ].join(" "),
};

const FIND_COMPETITORS: PromptChip = {
  label: "Find my competitors",
  blurb: "Who wins the searches you want, across your markets.",
  prompt: [
    "Find the domains this website competes with in search, across its markets.",
    "Keep only domains that chase the same searchers for the same thing; marketplaces, encyclopedias, forums and news sites share keywords with everyone and do not count.",
    "Show me the list with a reason for each, and save the ones I agree with.",
  ].join(" "),
};

const FIND_BACKLINKS: PromptChip = {
  label: "Find backlink opportunities",
  blurb: "Sites linking to your competitors but not to you.",
  prompt: [
    "Find sites that link to this website's saved competitors but not to this website.",
    "Keep the ones where a real editor could plausibly link here for the same reason; skip spam, directories that link anything, and the competitors themselves.",
    "Show me the shortlist, most competitors linked first, and save the ones I agree with.",
  ].join(" "),
};

const CLUSTER_SEARCH_CONSOLE: PromptChip = {
  label: "Cluster my Search Console queries",
  blurb: "Group the searches Google already shows you for, noise removed.",
  prompt: [
    "Build keyword clusters from this website's Search Console queries, the ones with the most impressions first.",
    "When it is done, tell me how many clusters came out, how many queries were dropped as noise or off-topic, and the biggest clusters by monthly searches.",
  ].join(" "),
};

const CLUSTER_RANKED: PromptChip = {
  label: "Cluster what I already rank for",
  blurb: "Group the keywords the vendor sees this site ranking for.",
  prompt: [
    "Build keyword clusters from the keywords this website already ranks for, the ones bringing the most traffic first.",
    "Then tell me which of the biggest clusters are worth pushing further.",
  ].join(" "),
};

const CLUSTER_GAPS: PromptChip = {
  label: "Find competitor keyword gaps",
  blurb: "Keywords two or more competitors rank for and you do not.",
  prompt: [
    "Build keyword clusters from the keywords two or more of my saved competitors rank for and this website does not.",
    "If fewer than two competitors are saved, say so and stop. Otherwise tell me the biggest gaps by monthly searches and which competitors own them.",
  ].join(" "),
};

export function desk(): PromptChip[] {
  return [
    TARGET_NEXT,
    BUILD_CLUSTERS,
    CLUSTER_SEARCH_CONSOLE,
    CLUSTER_RANKED,
    CLUSTER_GAPS,
    STRIKING,
    FIND_COMPETITORS,
    FIND_BACKLINKS,
    CHANGED,
  ];
}

export function cluster(mainKeyword: string): PromptChip[] {
  return [
    {
      label: "Plan a page for this cluster",
      blurb: "A brief for one page: title, H1, outline and the keywords it should cover.",
      prompt: [
        `Plan one page that targets the keyword cluster "${mainKeyword}".`,
        "Read the results that rank for it now and write a brief: the title, the H1, the meta description, an outline of what the page must cover, and the other keywords of the cluster it should answer.",
        "Say which results above it are weakest and what the page needs to beat them.",
      ].join(" "),
    },
    {
      label: "Why is this winnable?",
      blurb: "Walk through the results above and say which ones a good page can pass.",
      prompt: [
        `Explain the winnability score of the keyword cluster "${mainKeyword}".`,
        "Walk through the results above us one by one: their link strength against ours, whether they serve the search well, and the chance of passing each.",
        "Say plainly what the score cannot see, such as content quality.",
      ].join(" "),
    },
    {
      label: "Is a page of mine close?",
      blurb: "Check whether an existing page could be edited to own this instead.",
      prompt: [
        `Check whether an existing page of this website could own the keyword cluster "${mainKeyword}" instead of a new page.`,
        "Use Search Console data and the pages' text to find the nearest page, and say whether editing it beats writing a new one.",
      ].join(" "),
    },
  ];
}

export function competitors(): PromptChip[] {
  return [
    FIND_COMPETITORS,
    {
      label: "Clean up this list",
      blurb: "Drop marketplaces, forums and news sites that only share words with you.",
      prompt: [
        "Read the saved competitors of this website and tell me which do not belong: domains that share keywords with everyone rather than chasing the same searchers for the same thing.",
        "Remove them once I agree.",
      ].join(" "),
    },
    {
      label: "Compare me with a competitor",
      blurb: "Pick one domain and see where it outranks you and why.",
      prompt: [
        "I will name one of my competitors. Show me the searches where it outranks this website, which of its pages win them, and what those pages do that ours do not.",
      ].join(" "),
    },
  ];
}

export function backlinks(): PromptChip[] {
  return [
    FIND_BACKLINKS,
    {
      label: "Which are worth asking?",
      blurb: "Rank the saved sites by how plausible a link to you is, and drop the spam.",
      prompt: [
        "Read the saved backlink opportunities of this website and rank them by how plausible a link to us is.",
        "Remove the spam and the sites that would never link a business like this one, once I agree.",
      ].join(" "),
    },
    {
      label: "Why do they link to competitors?",
      blurb: "Read what each site links to and the reason, so the ask fits.",
      prompt: [
        "For the top saved backlink opportunities, find what they link to on my competitors' sites and why, so I know what to offer each one.",
      ].join(" "),
    },
  ];
}

export function tracked(): PromptChip[] {
  return [
    {
      label: "Track my main keywords",
      blurb: "Start tracking the main keyword of every cluster you plan to target.",
      prompt: [
        "Start tracking rankings and search volume for the main keyword of every keyword cluster with a winnability of 50 or more.",
        "Tell me how many keywords that is before you start, since tracking spends vendor credit.",
      ].join(" "),
    },
    {
      label: "Which pages are going up or down?",
      blurb: "Read the ranking history and name the movers, with the likely reason.",
      prompt: [
        "Read the ranking history of the tracked keywords and tell me which of this website's pages moved most, up and down, and over what period.",
        "For the biggest drops, say which result moved above us.",
      ].join(" "),
    },
    {
      label: "Is demand seasonal?",
      blurb: "Read monthly search volume and say when each keyword peaks.",
      prompt: [
        "Read the monthly search volume of the tracked keywords and tell me which are seasonal, when each one peaks, and how far ahead a page should be ready.",
      ].join(" "),
    },
    {
      label: "Who overtook me?",
      blurb: "For keywords you lost, find the result that moved above you.",
      prompt: [
        "For every tracked keyword where this website lost positions since the previous run, name the result that moved above us and what changed.",
      ].join(" "),
    },
  ];
}
