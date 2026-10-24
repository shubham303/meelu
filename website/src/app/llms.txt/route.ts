import { listPosts } from "@/lib/blog";
import { site } from "@/lib/site";

const tools = [
  ["seo-audit", "SEO audit of any site"],
  ["broken-link-checker", "Find dead links and 404s"],
  ["keyword-clustering-tool", "Cluster keywords into pages by search intent, checked against Google's top 10"],
  ["readability-checker", "Readability score and hard sentences"],
  ["similarity-checker", "Compare two texts or URLs"],
  ["ai-content-detector", "Score text as human or AI-written, in the browser"],
  ["review-sentiment-analyzer", "Label reviews and rank complaints"],
];

export function GET() {
  const posts = listPosts()
    .map((post) => `- [${post.title}](${site.url}/blog/${post.slug}): ${post.metaDescription}`)
    .join("\n");

  const body = `# ${site.name}

> ${site.description}

Meelu is in development and built in the open. The desktop app is out for macOS and Windows and needs a Meelu account. Crawling and the agent run on the user's computer; site data and third-party data lookups live on Meelu's server. Nothing changes on the user's site without their approval.

## Desks

- Site and Technical SEO: crawl the site, map internal links, find broken links, missing tags and pages that render differently on mobile
- SEO: Search Console and Google Analytics next to keyword volumes, Google's top 10, competitors and backlinks; keyword clusters with one page per search
- GEO: track questions people ask AI search, check whether a page answers each one and what ChatGPT, Claude and Google's AI Overview say and cite
- Content: write web pages for the user's own site (title, H1, meta description, slug, target keyword, body), checked on every save
- Social Listening: find conversations on Reddit, X, LinkedIn, Bluesky, Facebook, Hacker News, Stack Exchange, Dev.to, GitHub Issues and forums and Q&A sites across the web where a reply would help
- Find Leads: find people worth a personal message, with the posts behind each one; the user writes and sends the message
- Analytics and Reports: ask questions about Search Console and Analytics data, answered with charts and evidence, and keep the ones that matter

## Integrations

Per website, through Composio: Gmail, Outlook, Mailchimp and Kit (drafts only), Resend (sends only email the user approved), Webflow and Contentful (draft pages), HubSpot, Attio and Pipedrive (contacts and notes the user approves), Notion and Google Docs (new pages), Reddit, LinkedIn and GitHub (posts only a reply the user approved, never a new post). Google Search Console and Google Analytics 4 connect from the app.

## Pricing

- [Pricing](${site.url}/pricing): one plan on credits (1 credit = 1 US dollar). Each of the first five websites costs 1 credit a day and every website after that 0.5; external services (DataForSEO, Apify, OpenRouter) are charged per use. A new account's first website is free for one day; the agent can also run on the user's own LLM key.

## Open source

- [meelu-analytics-mcp](https://github.com/shubham303/meelu-analytics-mcp): 45 deterministic analysis tools for any MCP-capable assistant (MIT)

## Free tools

All run without sign-up; most run entirely in the browser.

- [All tools](${site.url}/tools)
${tools.map(([slug, line]) => `- [${line}](${site.url}/tools/${slug})`).join("\n")}

## Blog

${posts}

## Contact

- [Contact](${site.url}/contact): who builds Meelu and how to reach them
- Email: ${site.email}
- GitHub: ${site.github}
- RSS: ${site.url}/rss.xml

## Legal

- [Terms of service](${site.url}/terms): the terms covering the app, accounts and credits, the site and the free tools
- [Privacy policy](${site.url}/privacy): what the app and site collect, including Google Search Console and Analytics data, and how to delete it
`;

  return new Response(body, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
