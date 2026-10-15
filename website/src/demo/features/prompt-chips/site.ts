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

export function desk(): PromptChip[] {
  return [PROFILE, GAPS, BROKEN];
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
    "Strategy: related content. Connect informational pages that discuss the same subject so a reader who finishes one page has a natural next read.",
    "Links should come from live pages classified as informational, and while they can point to any page, prefer informational and hub pages as targets.",
    "A source-target pair qualifies only when the source passage genuinely discusses what the target page is about, not when the two merely share a keyword.",
    "When reviewing, keep a link only if you can name the specific sentence on the source page where it would sit and it would read as a helpful aside rather than an insertion.",
    "As a cap, a blog post should rarely receive more than three new links.",
  ].join(" "),
};

const LINK_MONEY: PromptChip = {
  label: "Send authority to money pages",
  blurb: "Point your strongest pages at the product and pricing pages that earn.",
  prompt: [
    "Strategy: authority to money pages. Move link equity from the pages that already have it to the pages that earn revenue.",
    "Links should come from the informational and hub pages with the highest link_score and the most inlinks, and they should point at pages classified money that have few inlinks or a low link_score.",
    "A source-target pair qualifies when the source's topic justifies sending a reader to that product, service or pricing page, so the reader feels helped rather than sold to.",
    "When reviewing, reject any pair where the money page is only tangentially related; one strong link is worth more than three weak ones.",
  ].join(" "),
};

const LINK_ORPHANS: PromptChip = {
  label: "Rescue orphan and deep pages",
  blurb: "Give pages nothing links to, or buried too deep, a way in.",
  prompt: [
    "Strategy: orphan and deep page rescue. Give a way in to pages nothing links to, and pull up pages buried four or more clicks from the home page.",
    "The targets are live indexable pages with zero inlinks, or a depth of four or more, that are not utility or legal pages; leave the sources unrestricted and let the search find them.",
    "A source-target pair qualifies when the target is relevant enough to earn a body link from that source, not merely any link at all.",
    "When reviewing, prefer sources that already rank or hold inlinks of their own, because a link from another orphan rescues nothing.",
    "Also add each target's title, H1 and the key phrases in its meta description as unlinked mentions, so passages that already name it get linked.",
  ].join(" "),
};

const LINK_MENTIONS: PromptChip = {
  label: "Link unlinked mentions",
  blurb: "Turn passages that already name a page's subject into links to it.",
  prompt: [
    "Strategy: unlinked mentions. Find passages that already name a page's subject without linking to it.",
    "The targets are money and hub pages, plus any page ranking between positions 8 and 15 in Search Console for a query with real impressions, and the phrases to look for are each target's title, its H1, the short key phrases in its meta description and those striking-distance queries; phrases match word for word, so never pass the whole meta description.",
    "A mention qualifies when it refers to what the target page is actually about, rather than a homonym or a word used in passing.",
    "When reviewing, remember the anchor is the mention itself, so reject it if wrapping that phrase in a link would mislead the reader about where it goes.",
  ].join(" "),
};

const LINK_FRESH: PromptChip = {
  label: "Link new pages from old ones",
  blurb: "Give every page published in the last 60 days a link from an established one.",
  prompt: [
    "Strategy: freshness. New pages start with no inlinks, so give each one a link from an established page in the same section.",
    "The targets are pages published in the last 60 days, and the sources are older pages in the same URL section with the most inlinks.",
    "A source-target pair qualifies when the older page discusses the topic the new page goes deeper on.",
    "When reviewing, one or two good sources per new page is enough; do not blanket a new post with links from everything that mentions it.",
  ].join(" "),
};

const LINK_SKELETON: PromptChip = {
  label: "Fix the site skeleton",
  blurb: "Home, hubs and utility pages linked the way the URL structure implies.",
  prompt: [
    "Strategy: site skeleton. Make sure the home page, the hub pages and the utility pages link to each other the way the URL structure implies.",
    "Use the hierarchy generator for this: home to and from every utility page, and each parent hub to its child hubs and back. Text similarity means nothing for these pages; structure is what decides.",
    "A pair qualifies unless the target is a page that should not be reachable from navigation at all, such as a thank-you page, a checkout step or internal search.",
    "When reviewing, keep in mind these links usually belong in navigation or the footer, so say that in the suggestion whenever a body link would read oddly.",
  ].join(" "),
};

const PRUNE_IRRELEVANT: PromptChip = {
  label: "Remove off-topic links",
  blurb: "Body links whose passage has nothing to do with the page they point at.",
  prompt: [
    "Strategy: prune off-topic links. Find body links where the passage around the anchor does not discuss what the target page is about.",
    "The candidates are every body link between two live indexable pages, excluding links to the home page and to hub pages. Write them to a workspace table with from_page_id, to_page_id and a reason, then run the removals generator over it; it scores each link by how little the anchor's passage relates to the target.",
    "A link qualifies as a removal when a reader following it would feel misdirected, because the two pages share no subject or the anchor promises something the target does not deliver.",
    "When reviewing, keep the removal only if you can say what the reader loses by following the link; a merely weak link is not a removal.",
  ].join(" "),
};

const PRUNE_OVERLINKED: PromptChip = {
  label: "Thin out over-linked pages",
  blurb: "Pages with far more body links than their length carries.",
  prompt: [
    "Strategy: thin out over-linked pages. A page's link budget is roughly three body links plus one per three hundred words, capped at fifteen, so find the pages far past that and propose removing the links that add the least.",
    "The candidates are body links from pages whose body-link count is more than twice their budget, excluding home and hub pages as sources. Write every such link to a workspace table with a reason naming how far over budget the source is, then run the removals generator.",
    "A link qualifies as a removal when the same target is already linked elsewhere on the page, the anchor is generic such as click here, read more or this page, or the target is a legal, utility or company page linked from body copy.",
    "When reviewing, prefer removing duplicates and generic anchors over removing the only link to a relevant page. Ranking never strips more than a third of a page's links at once, so propose freely.",
  ].join(" "),
};

const PRUNE_WEAK_TARGETS: PromptChip = {
  label: "Stop linking to dead-end pages",
  blurb: "Body links pointing at thin, noindex or redirecting pages.",
  prompt: [
    "Strategy: dead-end targets. Find the body links that send readers and link equity to pages that cannot use them.",
    "The candidates are body links whose target is noindex, redirects, returns an error, is blocked by robots, or is a shallow page with very little text. Write them to a workspace table with the target's problem as the reason, then run the removals generator.",
    "A link qualifies as a removal when the target's problem is not about to be fixed; where the target is a good page that merely redirects to a better URL, the suggestion should say to repoint the link rather than drop it.",
    "When reviewing, keep a link into a thin page the site plans to grow, and say so whenever the target looks like a stub in progress.",
  ].join(" "),
};

const PILLAR_CLUSTERS: PromptChip = {
  label: "Find topics missing a pillar page",
  blurb: "Groups of pages on one subject that no hub introduces and links.",
  prompt: [
    "Strategy: pillar pages from meaning. Cluster every embedded page by what it is about, and find the groups that no existing page introduces and links.",
    "Run the pillar generator with the job id alone; it clusters the pages, drops the small or loose groups, and skips a group a hub already covers. When a page partly covers a group, it becomes an expand suggestion for that page.",
    "A group qualifies when a reader would expect one page to cover the whole set and the site has none, which means the pages share a subject a person would search for rather than merely a format or a date.",
    "When reviewing, name the page the pillar should be, what it must cover, which of the member pages it links to and in what order, and which should link back. Reject a group that is really two topics, or that an existing hub already does the job for.",
  ].join(" "),
};

const PILLAR_FOLDERS: PromptChip = {
  label: "Give every section an index page",
  blurb: "URL folders with several pages and no page at the folder itself.",
  prompt: [
    "Strategy: section index pages. A URL folder with several live pages under it and no live page at the folder URL itself is a section without a front door.",
    "Build the groups with SQL over site_pages: group live pages by their parent path, keep the folders holding four or more pages where no live page sits at that path, and write group_key (the folder path), page_id and topic (the folder name, humanised) to a workspace table. Then run the pillar generator over that table.",
    "A group qualifies when the folder is a real topic, not a date archive, an author archive, a tag bucket or pagination.",
    "When reviewing, treat the pillar as the page that belongs at the folder URL, and say what it should tell a reader about the section and how it should list its pages.",
  ].join(" "),
};

const PILLAR_QUERIES: PromptChip = {
  label: "Build pillars for shared search queries",
  blurb: "Pages competing for the same queries in Search Console with no page that owns them.",
  prompt: [
    "Strategy: pillar pages from search demand. When several pages take impressions for the same head query and none of them ranks well, the site is answering that query in pieces and needs one page that owns it.",
    "Build the groups with SQL over site_search_daily for the last ninety days from max(day): queries with real impressions spread over three or more pages where the best position is worse than eight. Write group_key (the query), page_id and topic (the query) to a workspace table and run the pillar generator over it.",
    "A group qualifies when the query is a topic a single comprehensive page could own, rather than a brand term, a navigational query or a product name the pages already share.",
    "When reviewing, state the query the pillar targets and what each of the existing pages contributes, so the owner can see it is a consolidation and not a duplicate.",
  ].join(" "),
};

export function linkStrategies(): PromptChip[] {
  return [
    LINK_RELATED,
    LINK_MONEY,
    LINK_ORPHANS,
    LINK_MENTIONS,
    LINK_FRESH,
    LINK_SKELETON,
    PRUNE_IRRELEVANT,
    PRUNE_OVERLINKED,
    PRUNE_WEAK_TARGETS,
  ];
}

export function pillarStrategies(): PromptChip[] {
  return [PILLAR_CLUSTERS, PILLAR_FOLDERS, PILLAR_QUERIES];
}

export function structure(): PromptChip[] {
  return [...linkStrategies(), ...pillarStrategies()];
}
