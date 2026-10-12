import { listPosts } from "@/lib/blog";
import { site } from "@/lib/site";

function escape(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function GET() {
  const items = listPosts()
    .map(
      (post) => `    <item>
      <title>${escape(post.title)}</title>
      <link>${site.url}/blog/${post.slug}</link>
      <guid>${site.url}/blog/${post.slug}</guid>
      <description>${escape(post.description)}</description>
      <pubDate>${new Date(`${post.date}T00:00:00Z`).toUTCString()}</pubDate>
    </item>`,
    )
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>${escape(site.name)} Blog</title>
    <link>${site.url}/blog</link>
    <description>${escape(site.description)}</description>
    <image>
      <url>${site.url}/meelu-mark.png</url>
      <title>${escape(site.name)} Blog</title>
      <link>${site.url}/blog</link>
      <width>144</width>
      <height>144</height>
    </image>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
}
