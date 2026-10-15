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

## Pricing

- [Pricing](${site.url}/pricing): one plan on credits (1 credit = 1 US dollar). Each of the first five websites costs 0.4 credits a day and every website after that 0.2; external services (DataForSEO, Apify, OpenRouter) are charged per use. A new account's first website is free for three days; the agent can also run on the user's own LLM key.

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
