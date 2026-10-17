import type { PromptChip } from "./lib";

const TOPIC_PLAN: PromptChip = {
  label: "Plan content for a topic",
  blurb: "A hub page and supporting pages for a topic, as a plan you can review.",
  prompt: [
    "I will give you a topic. Before you start, ask me what the content is for, what value I want it to give readers, and whether I am planning a single page or a series of pages.",
    "Then build keyword clusters for the topic, add the related clusters I already have, and keep only the ones that truly fit the topic.",
    "Plan a hub page and the pages around it, each targeting one or more clusters. Check my existing pages and say which ones should be updated and which new pages should be added.",
    "Put the plan in a report. For each page to update, explain what to add, usually the clusters it should cover. For each new page, list what it should cover.",
    "Do not write the content itself. The report is for me to decide which pages to create.",
  ].join(" "),
};

const STRIKING_DISTANCE: PromptChip = {
  label: "Striking distance keywords",
  blurb: "Searches where you rank 8 or lower and get few clicks.",
  prompt: [
    "Find the searches where my site ranks at position 8 or lower, gets more than 10 impressions, and has a click-through rate under 5% or no clicks at all.",
    "List them with the page that ranks for each.",
  ].join(" "),
};

const LONG_TAIL: PromptChip = {
  label: "Long-tail keywords from People Also Ask",
  blurb: "Turn Google's questions and suggestions into long-tail keywords.",
  prompt: [
    "I will give you a keyword. Look at what Google shows for it: the People Also Ask questions and the autocomplete suggestions.",
    "Turn them into long-tail keywords, group them into clusters, and check their search volume.",
    "Give me the list ranked by intent, with commercial and transactional keywords first.",
  ].join(" "),
};

const SEED_IDEAS: PromptChip = {
  label: "Keyword ideas from a seed",
  blurb: "Related keywords for a topic, grouped and split by intent.",
  prompt: [
    "I will give you a seed keyword or topic. Find related and similar keywords and group them into clusters.",
    "Remove the clusters that do not match the original intent.",
    "Then tell me what clusters you found and how many of them are informational, commercial and transactional.",
  ].join(" "),
};

const MATCH_COMPETITOR: PromptChip = {
  label: "Content to match a competitor",
  blurb: "Keywords a competitor ranks for and you do not, with a page plan for each.",
  prompt: [
    "I will name a competitor's domain. Find the keywords it ranks for that my site does not, group them into clusters, and drop the noisy ones.",
    "Pick 10 clusters at random. For each one, check whether a page on my site already covers it, and suggest either editing that page or writing a new one.",
    "Also tell me which of my existing pages should link to it.",
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
  return [STRIKING_DISTANCE, DROPPED, INVISIBLE];
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

const BUILD_CLUSTERS: PromptChip = {
  label: "Build clusters for a topic",
  blurb: "Turn a few seed keywords into clusters, noise and off-topic searches removed.",
  prompt: [
    "I will name a topic. Choose a handful of seed keywords for it from what this website sells, show them to me, and once I agree build keyword clusters from them.",
    "When it is done, tell me how many clusters came out, how many keywords were dropped as noise or off-topic, and the biggest clusters by monthly searches.",
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

export function desk(): PromptChip[] {
  return [
    LONG_TAIL,
    SEED_IDEAS,
    MATCH_COMPETITOR,
    TOPIC_PLAN,
    STRIKING_DISTANCE,
    BUILD_CLUSTERS,
    CLUSTER_SEARCH_CONSOLE,
  ];
}

export const SCORE_CLUSTERS: PromptChip = {
  label: "Score my clusters",
  blurb: "Score the keyword clusters that have no score yet.",
  prompt:
    "Score my keyword clusters that have no score yet, starting with the ones people search most. Then show me the best ones to target.",
};

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
    {
      label: "Who holds this keyword?",
      blurb: "Twelve months of results: the domains that stay in the top 10.",
      prompt: [
        `Read twelve months of results-page history for "${mainKeyword}" and tell me which domains stayed in the top 10 most consistently, ignoring the ones that showed up only now and then.`,
        "Say where this website stood over the same months, and which of the consistent domains are not saved as competitors yet; ask before saving any.",
      ].join(" "),
    },
  ];
}

export function competitors(): PromptChip[] {
  return [
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
    {
      label: "Why do they link to competitors?",
      blurb: "Read what each site links to and the reason, so the ask fits.",
      prompt: [
        "For the top backlink opportunities of this website, find what they link to on my competitors' sites and why, so I know what to offer each one.",
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
        "Start tracking search volume for the main keyword of every keyword cluster with a winnability of 50 or more.",
        "Tell me how many keywords that is before you start, since tracking spends vendor credit.",
      ].join(" "),
    },
    {
      label: "Which pages are going up or down?",
      blurb: "Read Search Console positions and name the movers.",
      prompt: [
        "Read this website's Search Console position for the tracked keywords, month by month in each market, and tell me which of its pages moved most, up and down, and over what period.",
      ].join(" "),
    },
    {
      label: "Is demand seasonal?",
      blurb: "Read monthly search volume and say when each keyword peaks.",
      prompt: [
        "Read the monthly search volume of the tracked keywords and tell me which are seasonal, when each one peaks, and how far ahead a page should be ready.",
      ].join(" "),
    },
  ];
}
