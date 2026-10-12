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


const LINK_RELATED: PromptChip = {
  label: "Link related articles",
  blurb: "Connect articles on the same subject so a reader always has a next read.",
  prompt: [
    "Strategy: related content. Connect informational pages that discuss the same subject so a reader who finishes one has the natural next read.",
    "From set: live pages classified informational. To set: unrestricted, but prefer informational and hub pages.",
    "A pair passes when the source passage genuinely discusses what the target page is about, not when they merely share a keyword.",
    "For the review: keep a link only if you can name the sentence on the source where it would sit and it would read as a helpful aside, not an insertion.",
    "Cap: a blog post rarely takes more than three new links.",
  ].join(" "),
};

const LINK_MONEY: PromptChip = {
  label: "Send authority to money pages",
  blurb: "Point your strongest pages at the product and pricing pages that earn.",
  prompt: [
    "Strategy: authority to money pages. Move link equity from the pages that have it to the pages that earn revenue.",
    "From set: pages with the highest link_score and inlinks that are informational or hub. To set: pages classified money with few inlinks or a low link_score.",
    "A pair passes when the source topic justifies sending a reader to that product, service or pricing page — the reader should feel helped, not sold to.",
    "For the review: reject any pair where the money page is only tangentially related; one strong link beats three weak ones.",
  ].join(" "),
};

const LINK_ORPHANS: PromptChip = {
  label: "Rescue orphan and deep pages",
  blurb: "Give pages nothing links to, or buried too deep, a way in.",
  prompt: [
    "Strategy: orphan and deep page rescue. Give a way in to pages nothing links to, and pull up pages buried four or more clicks deep.",
    "To set: live pages with zero inlinks, or depth of four or more, that are indexable and not utility or legal. From set: unrestricted; let the search find the sources.",
    "A pair passes when the target is relevant enough to earn a body link from that source, not just any link.",
    "For the review: prefer sources that already rank or have inlinks themselves; a link from another orphan rescues nothing.",
    "Also add the target's title and H1 as unlinked mentions so passages that already name it get linked.",
  ].join(" "),
};

const LINK_MENTIONS: PromptChip = {
  label: "Link unlinked mentions",
  blurb: "Turn passages that already name a page's subject into links to it.",
  prompt: [
    "Strategy: unlinked mentions. Find passages that already name a page's subject without linking to it.",
    "To set: money and hub pages, plus any page ranking at positions 8 to 15 in Search Console for a query with real impressions.",
    "Phrases per target: its title, its H1, and those striking-distance queries.",
    "A pair passes when the mention refers to what the target page is actually about, not a homonym or a passing word.",
    "For the review: the anchor is the mention itself; reject if wrapping that phrase in a link would mislead the reader about where it goes.",
  ].join(" "),
};

const LINK_FRESH: PromptChip = {
  label: "Link new pages from old ones",
  blurb: "Give every page published in the last 60 days a link from an established one.",
  prompt: [
    "Strategy: freshness. New pages start with no inlinks; give each one a link from an established page in the same section.",
    "To set: pages published in the last 60 days. From set: older pages in the same URL section with the most inlinks.",
    "A pair passes when the older page discusses the topic the new page goes deeper on.",
    "For the review: one or two good sources per new page is enough; do not blanket a new post with links from everything.",
  ].join(" "),
};

const LINK_SKELETON: PromptChip = {
  label: "Fix the site skeleton",
  blurb: "Home, hubs and utility pages linked the way the URL structure implies.",
  prompt: [
    "Strategy: site skeleton. Make sure the home page, the hub pages and the utility pages link to each other the way the URL structure implies.",
    "Use the hierarchy generator: home to and from every hub and utility page, parent hub to child hub and back, and sibling hubs to each other. Text similarity means nothing for these pages; structure does.",
    "A pair passes unless the target is a page that should not be reachable from navigation at all (thank-you pages, checkout steps, internal search).",
    "For the review: these links usually belong in navigation or footer; say so in the suggestion when a body link would be odd.",
  ].join(" "),
};

const LINK_SILO: PromptChip = {
  label: "Tighten a topic silo",
  blurb: "Keep a section's pages linking to each other more than outward.",
  prompt: [
    "Strategy: silo consistency. I will name a section or topic. Pages inside it should link to each other more than they link out.",
    "From set and to set: the pages in that section, by URL path or by topic cluster.",
    "A pair passes when the two pages cover neighbouring subtopics of the same theme, so the reader stays inside the silo.",
    "For the review: prefer links that close a gap in the silo — a page in the section that nothing else in the section links to — over links between pages already well connected.",
  ].join(" "),
};

const PRUNE_IRRELEVANT: PromptChip = {
  label: "Remove off-topic links",
  blurb: "Body links whose passage has nothing to do with the page they point at.",
  prompt: [
    "Strategy: prune off-topic links. Find body links where the passage around the anchor does not discuss what the target page is about.",
    "Candidates: every body link between two live, indexable pages, excluding links to the home page and to hub pages. Write them to a workspace table with from_page_id, to_page_id and a reason, then run the removals generator on it; it scores each link by how little the anchor's passage relates to the target.",
    "A link passes as a removal when a reader following it would feel misdirected: the two pages share no subject, or the anchor promises something the target does not deliver.",
    "For the review: keep the removal only when you can say what the reader loses by following the link; a merely weak link is not a removal.",
  ].join(" "),
};

const PRUNE_OVERLINKED: PromptChip = {
  label: "Thin out over-linked pages",
  blurb: "Pages with far more body links than their length carries.",
  prompt: [
    "Strategy: thin out over-linked pages. A page's link budget is roughly three body links plus one per three hundred words, capped at fifteen; find pages far past that and propose removing the links that add the least.",
    "Candidates: body links from pages whose body-link count exceeds twice their budget, excluding home and hub pages as sources. Write every such link to a workspace table with a reason naming how far over budget the source is, then run the removals generator.",
    "A link passes as a removal when the same target is linked more than once from the page, the anchor is generic (click here, read more, this page), or the target is a legal, utility or company page linked from body copy.",
    "For the review: prefer removing duplicates and generic anchors over removing the only link to a relevant page. Rank never strips more than a third of a page's links at once, so propose freely.",
  ].join(" "),
};

const PRUNE_WEAK_TARGETS: PromptChip = {
  label: "Stop linking to dead-end pages",
  blurb: "Body links pointing at thin, noindex or redirecting pages.",
  prompt: [
    "Strategy: dead-end targets. Body links that send readers and link equity to pages that cannot use them.",
    "Candidates: body links whose target is noindex, redirects, returns an error, is blocked by robots, or is a shallow page with very little text. Write them to a workspace table with the target's problem as the reason, then run the removals generator.",
    "A link passes as a removal when the target's problem is not about to be fixed; if the target is a good page that merely redirects to a better URL, the suggestion should say to repoint the link rather than drop it.",
    "For the review: a link into a thin page that the site plans to grow should be kept; say so when the target looks like a stub in progress.",
  ].join(" "),
};

const PILLAR_CLUSTERS: PromptChip = {
  label: "Find topics missing a pillar page",
  blurb: "Groups of pages on one subject that no hub introduces and links.",
  prompt: [
    "Strategy: pillar pages from meaning. Cluster every embedded page by what it is about and find the groups no existing page introduces and links.",
    "Run the pillar generator with the job id alone; it clusters, drops small or loose groups, and skips a group a hub already covers. When a page partly covers a group it becomes an expand suggestion for that page.",
    "A group passes when a reader would expect one page to cover the whole set and the site has none: the pages share a subject a person would search for, not merely a format or a date.",
    "For the review: name the page the pillar should be, what it must cover, which of the member pages it links to in what order, and which should link back. Reject a group that is really two topics or that an existing hub already does the job for.",
  ].join(" "),
};

const PILLAR_FOLDERS: PromptChip = {
  label: "Give every section an index page",
  blurb: "URL folders with several pages and no page at the folder itself.",
  prompt: [
    "Strategy: section index pages. A URL folder with several live pages under it and no live page at the folder URL itself is a section without a front door.",
    "Build the groups with SQL over site_pages: group live pages by their parent path, keep folders with four or more pages where no live page sits at that path, and write group_key (the folder path), page_id and topic (the folder name, humanised) to a workspace table. Run the pillar generator with that table.",
    "A group passes when the folder is a real topic and not a date archive, an author archive, a tag bucket or pagination.",
    "For the review: the pillar is the page at the folder URL; say what it should say about the section and how it should list its pages.",
  ].join(" "),
};

const PILLAR_QUERIES: PromptChip = {
  label: "Build pillars for shared search queries",
  blurb: "Pages competing for the same queries in Search Console with no page that owns them.",
  prompt: [
    "Strategy: pillar pages from search demand. When several pages take impressions for the same head query and none ranks well, the site is answering it in pieces and needs one page that owns it.",
    "Build the groups with SQL over site_search_daily for the last ninety days from max(day): queries with real impressions spread over three or more pages where the best position is worse than eight. Write group_key (the query), page_id and topic (the query) to a workspace table and run the pillar generator on it.",
    "A group passes when the query is a topic a single comprehensive page could own, not a brand term, a navigational query or a product name the pages already share.",
    "For the review: state the query the pillar targets and what the existing pages each contribute, so the owner can see it is a consolidation, not a duplicate.",
  ].join(" "),
};

export function structure(): PromptChip[] {
  return [
    LINK_RELATED,
    LINK_MONEY,
    LINK_ORPHANS,
    LINK_MENTIONS,
    LINK_FRESH,
    LINK_SKELETON,
    LINK_SILO,
    PRUNE_IRRELEVANT,
    PRUNE_OVERLINKED,
    PRUNE_WEAK_TARGETS,
    PILLAR_CLUSTERS,
    PILLAR_FOLDERS,
    PILLAR_QUERIES,
  ];
}
