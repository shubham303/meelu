export type UseCaseStep = { title: string; body: string };

export type FreeTool = { href: string; name: string; body: string };

export type UseCase = {
  slug: string;
  name: string;
  summary: string;
  title: string;
  description: string;
  metaTitle: string;
  metaDescription: string;
  problem: string;
  steps: UseCaseStep[];
  outcomes: string[];
  table?: { title: string; rows: { task: string; byHand: string; withMeelu: string }[] };
  prompts: string[];
  promptsTitle?: string;
  docsHref: string;
  freeTools?: FreeTool[];
};

export const useCases: UseCase[] = [
  {
    slug: "seo",
    name: "SEO",
    summary:
      "Group your keywords into clusters, find the ones you almost rank for, and plan the pages to write.",
    title:
      "A keyword clustering tool that plans your content.",
    description:
      "Meelu groups your keywords into clusters, one page per cluster. It uses your Search Console data to find keywords you almost rank for. Then it plans the pages, from one main page per topic to the pages that support it.",
    metaTitle:
      "Keyword clustering tool and SEO content planning | Meelu",
    metaDescription:
      "Cluster keywords by the Google results they share, find striking distance keywords in Search Console, and plan hub and supporting pages. Meelu suggests, you decide.",
    problem:
      "Keyword research tools give you a long list. They do not tell you which keywords belong on the same page. So you write one page per keyword, and your pages end up competing with each other.",
    steps: [
      {
        title: "Collect keywords",
        body: "Meelu starts from your Search Console queries, a topic you name, or the keywords your competitors rank for. It drops keywords with almost no searches and ones that are off topic, like other brands or job searches.",
      },
      {
        title: "Group them into clusters",
        body: "Keywords that show the same Google results go into one cluster. One page can rank for the whole cluster. Each cluster gets a main keyword, a search intent and a label for how close the searcher is to buying.",
      },
      {
        title: "Plan the pages",
        body: "For one cluster, Meelu writes a page brief or tells you which of your pages could rank for it. For a whole topic, it plans a hub page and the pages that support it.",
      },
    ],
    outcomes: [
      "Keyword clusters with monthly searches, search intent and a hot, warm or cold label",
      "Striking distance keywords: queries at position 8 or lower that get impressions but few clicks",
      "Page briefs with a title, H1, meta description, outline and the keywords to cover",
      "Topic plans with a hub page, supporting pages, and the pages you already have that need an update",
      "Twelve months of search demand for keywords you track, next to your position in Search Console",
      "Sites that link to your competitors but not to you, with spam and paid links removed",
    ],
    table: {
      title: "Where your SEO time goes",
      rows: [
        { task: "Audit the site", byHand: "A full day, once a month", withMeelu: "Every crawl" },
        { task: "Keyword research", byHand: "Hours in a spreadsheet", withMeelu: "A sorted list" },
        { task: "Check AI answers", byHand: "One question at a time", withMeelu: "Your questions, tracked" },
        { task: "Find threads to answer", byHand: "Doom scrolling social media", withMeelu: "Found and sorted for you" },
        { task: "Write a page", byHand: "Start from nothing", withMeelu: "Start from a draft" },
      ],
    },
    prompts: [
      "Cluster my Search Console queries",
      "Show my striking distance keywords",
      "Plan a hub page and supporting pages for a topic",
      "Is a page of mine close to owning this cluster?",
      "Which sites link to my competitors but not to me?",
    ],
    docsHref: "/docs/seo",
    freeTools: [
      { href: "/tools/keyword-clustering-tool", name: "Keyword clustering tool", body: "Paste a list of keywords and group them by the Google results they share." },
    ],
  },
  {
    slug: "ai-search",
    name: "AI search (GEO)",
    summary:
      "See whether ChatGPT, Claude and Google's AI Overview cite you, and what your page is missing.",
    title:
      "AI search optimization: get cited by ChatGPT, Claude and Google.",
    description:
      "Meelu tracks the questions your buyers ask AI search. For each one, it checks how well your page answers it, and what ChatGPT, Claude and Google's AI Overview say and cite.",
    metaTitle:
      "AI search optimization and AI visibility tool (GEO) | Meelu",
    metaDescription:
      "Generative engine optimization for your site: check if ChatGPT, Claude and Google's AI Overview cite you, see which points your page misses, and get the next step.",
    problem:
      "More buyers now ask ChatGPT before they search Google. AI visibility tools can tell you that you were not cited. They rarely tell you why, or what to change on your page.",
    steps: [
      {
        title: "Break the question down",
        body: "Meelu works out what the person wants: to learn, compare, buy or find one site. Then it lists every point a full answer has to cover.",
      },
      {
        title: "Check your page",
        body: "It finds the pages on your site closest to the question and reads them. It marks each point as answered, partly answered or missing, and quotes the passage it found.",
      },
      {
        title: "Ask the AI engines",
        body: "It asks ChatGPT and Claude with web search on, and reads Google's AI Overview. You see each answer, the sources it cites, and whether your site is one of them.",
      },
    ],
    outcomes: [
      "A verdict for each question: no page, partly answered, answered but ranking low, or covered",
      "The exact points your page is missing",
      "The sources each AI answer cites, and what your page covers that they do not",
      "A next step for each question, such as writing a page, adding to one, or letting AI crawlers in",
      "Up to 100 tracked questions per website",
    ],
    prompts: [
      "Suggest the questions my buyers ask AI search",
      "Which questions have no page on my site?",
      "Why does ChatGPT cite my competitor and not me?",
    ],
    docsHref: "/docs/geo",
    freeTools: [
      { href: "/tools/seo-audit", name: "SEO audit", body: "Check any page for robots.txt blocks, missing tags and other problems that keep it out of search." },
    ],
  },
  {
    slug: "technical-seo",
    name: "Technical SEO",
    summary:
      "A technical SEO audit that also checks what Google sees after JavaScript runs.",
    title:
      "A technical SEO audit that sees what Google sees.",
    description:
      "Meelu crawls your site and loads each page the way Googlebot does, on desktop and on mobile. It finds the problems that stop Google and AI crawlers from reading your pages, and sorts them by how much they matter.",
    metaTitle:
      "Technical SEO audit tool with JavaScript checks | Meelu",
    metaDescription:
      "Run a technical SEO site audit on up to 10,000 pages. Find indexing, canonical, hreflang, redirect and JavaScript problems, sorted by severity. You fix what matters first.",
    problem:
      "A full site audit takes a day, so most sites get one and then never again. Many AI crawlers also skip JavaScript. If your text or links load with JavaScript, those crawlers never see them.",
    steps: [
      {
        title: "Crawl the site",
        body: "Meelu crawls your site from your computer, up to 10,000 pages. The crawl is free, and it runs again about once a day while the app is open.",
      },
      {
        title: "Check the raw and rendered page",
        body: "Static checks read the HTML your server sends. Rendering checks load each page as Googlebot on desktop and on mobile, and compare the two versions.",
      },
      {
        title: "Fix what matters first",
        body: "Each problem gets a severity, from Fix now to Polish, with the pages it affects. You fix it on your site, or turn it down if it does not apply to you.",
      },
    ],
    outcomes: [
      "Indexing problems, such as pages blocked by robots.txt or missing from your sitemap",
      "Canonical tags that are missing, point to the wrong page, or change after JavaScript runs",
      "Hreflang tags with wrong language codes or missing return links",
      "Redirect chains, http and https mix-ups, and duplicate www versions of your site",
      "Text, links, titles or structured data that appear only after JavaScript runs",
      "Pages that look different on mobile",
      "AI crawlers such as GPTBot and ClaudeBot blocked by robots.txt or your firewall",
    ],
    prompts: [
      "What should I fix first on my site?",
      "Which pages hide their text behind JavaScript?",
      "Why is this page not indexed?",
    ],
    docsHref: "/docs/site/technical-seo",
    freeTools: [
      { href: "/tools/seo-audit", name: "SEO audit", body: "Check any site for common technical SEO problems, free." },
      { href: "/tools/broken-link-checker", name: "Broken link checker", body: "Find dead links and 404 pages on a site." },
    ],
  },
  {
    slug: "internal-links",
    name: "Internal links",
    summary:
      "Find orphan pages and pages buried too deep, and get the internal links that fix them.",
    title:
      "An internal linking tool for orphan pages and lost link value.",
    description:
      "Meelu maps the links between your pages after each crawl. It finds pages that nothing links to, and pages too many clicks from your home page. Then it suggests which links to add or remove, and why.",
    metaTitle:
      "Internal linking tool for SEO: orphan pages and link suggestions | Meelu",
    metaDescription:
      "Find orphan pages and pages buried too deep, then get internal linking suggestions for SEO, with the reason for each link. You make every change yourself.",
    problem:
      "Internal links help Google find your pages and show which ones matter most. Checking them by hand across hundreds of pages takes too long, so orphan pages and dead links pile up.",
    steps: [
      {
        title: "Map your links",
        body: "After each crawl, Meelu records every internal link and counts how many clicks each page is from your home page.",
      },
      {
        title: "Find the problem pages",
        body: "It lists orphan pages that nothing links to, pages you cannot reach by clicking from the home page, and pages four or more clicks deep.",
      },
      {
        title: "Suggest links",
        body: "Choose a strategy, such as linking related articles. Meelu suggests links to add or remove, each with the source page, the target page and the reason. You make the change in your own editor.",
      },
    ],
    outcomes: [
      "Orphan, unreachable and deep pages, with a chart of how deep your pages sit",
      "Links from your strongest pages to the product and pricing pages that earn",
      "Places where you mention a topic but do not link to its page yet",
      "Links between related articles, so every reader has a next page",
      "Links to remove, such as off-topic links and links to dead or redirected pages",
      "Pillar page ideas where several pages cover the same topic",
    ],
    prompts: [
      "Which pages are orphans?",
      "Suggest internal links to my most important pages",
      "Which topics need a pillar page?",
    ],
    docsHref: "/docs/site/structure",
    freeTools: [
      { href: "/tools/broken-link-checker", name: "Broken link checker", body: "Find internal links that point to dead pages." },
    ],
  },
  {
    slug: "content-writing",
    name: "Content writing",
    summary:
      "An SEO content writer that knows your site, your keywords and your existing pages.",
    title:
      "An SEO content writer that knows your site.",
    description:
      "Meelu writes page drafts from your keyword clusters and search data. Each draft has a title, H1, meta description and slug, and links to pages you already have. Meelu checks the draft, and you publish it.",
    metaTitle:
      "SEO content writer for your own site | Meelu",
    metaDescription:
      "Write SEO content from your own keyword clusters and Search Console data. Drafts come with a title, meta description, internal links and checks. Meelu never publishes; you do.",
    problem:
      "Most AI writers do not know your site. They pick keywords you cannot rank for, repeat pages you already have, and add no internal links. The new page then competes with your own pages.",
    steps: [
      {
        title: "Pick what to write",
        body: "Start from a keyword cluster, a keyword you almost rank for, or an AI search question you have no page for. Meelu sets one target keyword for the page.",
      },
      {
        title: "Get a draft",
        body: "The draft has a title, H1, meta description, slug and body. It covers the keywords in the cluster and links to related pages on your site.",
      },
      {
        title: "Check it and publish",
        body: "Meelu checks the page every time you save it. You copy the page to your site, or save it as a draft in Webflow or Contentful.",
      },
    ],
    outcomes: [
      "One target keyword per page, so your pages do not compete with each other",
      "Internal links to pages you already have",
      "Warnings for long titles, a missing H1, meta description length and a missing target keyword",
      "Readability, similarity and AI detection checks when you ask",
      "Nothing published without you",
    ],
    prompts: [
      "Write a page for my best keyword cluster",
      "Draft a page for the AI search question I have no page for",
      "Improve the intro of this draft",
    ],
    docsHref: "/docs/content",
    freeTools: [
      { href: "/tools/readability-checker", name: "Readability checker", body: "See how easy your text is to read, and which sentences are hard." },
      { href: "/tools/similarity-checker", name: "Similarity checker", body: "Compare two texts or pages to see how close they are." },
      { href: "/tools/ai-content-detector", name: "AI content detector", body: "Check whether text reads as written by a person or by AI." },
    ],
  },
  {
    slug: "social-listening",
    name: "Social listening",
    summary:
      "A social listening tool that finds people asking for a product like yours.",
    title:
      "A social listening tool that finds people asking for you.",
    description:
      "Tell Meelu what conversations you want to join, in plain words. It searches Reddit, X, LinkedIn, Hacker News and more, and keeps only the posts that really match. You decide which ones to answer.",
    metaTitle:
      "Social listening tool and Reddit monitoring | Meelu",
    metaDescription:
      "Monitor Reddit, X, LinkedIn, Hacker News and forums for posts where people ask for a product like yours. Meelu filters out the noise and drafts a reply. You decide what to post.",
    problem:
      "Most social listening tools match keywords. That brings hundreds of posts a week, and only a few are people actually asking for a tool like yours. Finding those few takes hours.",
    steps: [
      {
        title: "Say what you want to hear",
        body: "Write one sentence for each kind of conversation, such as \"people asking which tool tracks their Google rankings\". Meelu turns each sentence into searches.",
      },
      {
        title: "Meelu searches and filters",
        body: "It searches the platforms you pick. Then it reads each post and keeps only the ones that match your sentence, with the reason it kept them.",
      },
      {
        title: "You reply",
        body: "Meelu can draft a reply that answers the question first. You post it yourself, or approve it and let Meelu post it from an account you linked.",
      },
    ],
    outcomes: [
      "Posts from Reddit, X, LinkedIn, Facebook, Hacker News, Stack Exchange, Dev.to, GitHub, Bluesky and forums",
      "A reason for every post, so you can skim the list quickly",
      "Reply drafts that fit the platform, with no hashtags or sales tone",
      "Nothing posted without your approval",
    ],
    promptsTitle: "Lines to listen for",
    prompts: [
      "People asking which tool tracks their Google rankings",
      "Founders complaining that their traffic dropped",
      "Marketers asking for an alternative to a tool I compete with",
    ],
    docsHref: "/docs/social-listening",
  },
  {
    slug: "find-leads",
    name: "Find leads",
    summary:
      "A lead generation tool that finds people who just said they need what you sell.",
    title:
      "A lead generation tool that finds people who need you now.",
    description:
      "Describe the people you want to reach in one sentence. Meelu finds people who posted about the problem, matching LinkedIn profiles, and small businesses with their own website. Each lead comes with the reason it fits.",
    metaTitle:
      "Lead generation tool: find leads who need your product | Meelu",
    metaDescription:
      "Find leads who posted about the problem you solve, matching LinkedIn profiles and businesses with public emails. Each lead has a reason and an opening line. You send every message.",
    problem:
      "Bought lead lists match a job title and nothing more, so most people on them never reply. The best leads are people who said in public that they have the problem. Finding them by hand takes hours.",
    steps: [
      {
        title: "Describe who you want",
        body: "Write one sentence that says who they are and what shows they need you. For example, \"owners of small Shopify stores who say their Google traffic dropped\".",
      },
      {
        title: "Meelu searches and checks",
        body: "It looks for people who posted about it, matching LinkedIn profiles and businesses with their own site. It drops anyone who does not fit, and runs new searches, up to 10 rounds, until it finds enough.",
      },
      {
        title: "You reach out",
        body: "Each lead shows why it fits, the posts behind it, and an idea for your first line. You write and send the message, then mark the lead contacted.",
      },
    ],
    outcomes: [
      "People who posted about the problem in the last 30 days",
      "LinkedIn profiles that match the role you described",
      "Businesses with their own site, with an email only when the page shows one",
      "A reason and an opening line for every lead",
      "No messages sent for you",
    ],
    promptsTitle: "Briefs to try",
    prompts: [
      "Owners of small Shopify stores who say their Google traffic dropped",
      "Freelance web designers who hand sites to clients without SEO reports",
      "SaaS founders asking how to get their first users",
    ],
    docsHref: "/docs/find-leads",
  },
  {
    slug: "data-analysis",
    name: "Data analysis",
    summary:
      "Ask questions about your Search Console and Google Analytics data, and get answers with charts.",
    title:
      "SEO analytics: ask your Search Console and GA4 data anything.",
    description:
      "Ask a question about your traffic in plain words. Meelu analyzes your Search Console and Google Analytics data, and answers with the number, a chart and the pages behind it.",
    metaTitle:
      "SEO analytics for Search Console and Google Analytics | Meelu",
    metaDescription:
      "Analyze Search Console and GA4 data by asking questions in plain English. Compare periods, spot sudden changes, see seasonality and forecast clicks, with charts and evidence.",
    problem:
      "Search Console and Google Analytics hold the answers, but getting them means exports and spreadsheets. It is also hard to tell whether a drop is real or just normal ups and downs.",
    steps: [
      {
        title: "Ask a question",
        body: "For example, \"which queries gain impressions but lose clicks?\". You do not need to know which method to use.",
      },
      {
        title: "Meelu runs the analysis",
        body: "It works on your own data: Search Console, Google Analytics, your crawled pages, your site audit and your content.",
      },
      {
        title: "Read the answer",
        body: "The answer starts with the number. It says how Meelu got it, how far to trust it, and which pages and dates are behind it. Save it as a report if you want to keep it.",
      },
    ],
    outcomes: [
      "Comparisons between two periods that say whether a change is real or just noise",
      "The day a trend changed, and the pages or queries that stand out",
      "Weekly and yearly patterns, and forecasts with a range",
      "What moves together, such as position and click-through rate",
      "Charts and reports you can save, export and share",
    ],
    prompts: [
      "Where did clicks change in the last 28 days, and which pages drove it?",
      "Which queries gain impressions but lose clicks?",
      "Forecast organic clicks for the next 8 weeks",
    ],
    docsHref: "/docs/analytics",
  },
];

export function getUseCase(slug: string): UseCase | undefined {
  return useCases.find((useCase) => useCase.slug === slug);
}
