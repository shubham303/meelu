import type { MetadataRoute } from "next";
import { listPosts } from "@/lib/blog";
import { site } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const posts = listPosts().map((post) => ({
    url: `${site.url}/blog/${post.slug}`,
    lastModified: new Date(`${post.date}T00:00:00Z`),
  }));

  return [
    { url: site.url, priority: 1 },
    { url: `${site.url}/tools/seo-audit`, priority: 0.9 },
    { url: `${site.url}/tools/broken-link-checker`, priority: 0.9 },
    { url: `${site.url}/tools/keyword-clustering-tool`, priority: 0.9 },
    { url: `${site.url}/tools/readability-checker`, priority: 0.9 },
    { url: `${site.url}/tools/similarity-checker`, priority: 0.9 },
    { url: `${site.url}/tools/ai-content-detector`, priority: 0.9 },
    { url: `${site.url}/tools/review-sentiment-analyzer`, priority: 0.9 },
    { url: `${site.url}/download`, priority: 0.8 },
    { url: `${site.url}/pricing`, priority: 0.8 },
    { url: `${site.url}/tools`, priority: 0.7 },
    { url: `${site.url}/blog`, priority: 0.8 },
    { url: `${site.url}/contact`, priority: 0.5 },
    { url: `${site.url}/terms`, priority: 0.3 },
    { url: `${site.url}/privacy`, priority: 0.3 },
    ...posts,
  ];
}
