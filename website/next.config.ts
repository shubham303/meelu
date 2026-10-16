import type { NextConfig } from "next";
import { createMDX } from "fumadocs-mdx/next";

const retiredPosts = [
  "crm-lead-analysis",
  "csv-upload-vs-analytics-engine",
  "email-marketing-analysis",
  "ga4-search-console-analysis",
  "hotel-booking-analysis",
  "how-to-analyze-any-data-with-ai",
  "introducing-meelu-analytics",
  "paid-ads-analysis",
  "real-estate-analysis",
  "saas-churn-analysis",
  "shopify-store-analysis",
  "small-business-expense-analysis",
];

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    // Tailwind keeps the stylesheet small, so ship it inside the HTML and skip
    // the render-blocking request that was delaying the hero heading.
    inlineCss: true,
    globalNotFound: true,
  },
  async redirects() {
    // The site lives on the bare host (site.url, canonicals and the sitemap all
    // say so). Send www there path for path so the two never split links,
    // crawls or ranking between them.
    return [
      {
        source: "/:path*",
        has: [{ type: "host", value: "www.meelu.tech" }],
        destination: "https://meelu.tech/:path*",
        permanent: true,
      },
      // The per-dataset walkthroughs were folded into one guide. Send their
      // links and rankings there rather than to a 404.
      ...retiredPosts.map((slug) => ({
        source: `/blog/${slug}`,
        destination: "/blog/analyze-tabular-data-with-meelu-analytics-mcp",
        permanent: true,
      })),
      // The open source pages were folded into the same guide, which links
      // to the repository for setup.
      {
        source: "/open-source/:path*",
        destination: "/blog/analyze-tabular-data-with-meelu-analytics-mcp",
        permanent: true,
      },
    ];
  },
};

const withMDX = createMDX();

export default withMDX(nextConfig);
