import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeSlug from "rehype-slug";
import rehypeStringify from "rehype-stringify";
import { visit } from "unist-util-visit";
import type { Root, Element } from "hast";
import { imageSize } from "image-size";

export type PostMeta = {
  slug: string;
  title: string;
  description: string;
  /** Shorter forms for the <title> and meta description; fall back to title and description. */
  metaTitle: string;
  metaDescription: string;
  /** First image in the post, as a site-relative path, if there is one. */
  image: string | null;
  date: string;
  tags: string[];
};

export type Post = PostMeta & {
  html: string;
};

const postsDir = path.join(process.cwd(), "content", "blog");
const publicDir = path.join(process.cwd(), "public");

/**
 * Give every image that lives in /public its width and height so the browser can
 * reserve the space before the file arrives, and lazy-load everything below the fold.
 */
function rehypeImageDimensions() {
  return (tree: Root) => {
    visit(tree, "element", (node: Element) => {
      if (node.tagName !== "img" || typeof node.properties.src !== "string") return;
      const src = node.properties.src;
      if (!src.startsWith("/")) return;
      const file = path.join(publicDir, src);
      if (!path.resolve(file).startsWith(publicDir) || !fs.existsSync(file)) return;
      const { width, height } = imageSize(fs.readFileSync(file));
      if (!width || !height) return;
      node.properties.width = width;
      node.properties.height = height;
      node.properties.loading = "lazy";
      node.properties.decoding = "async";
    });
  };
}

function firstImage(content: string): string | null {
  return content.match(/!\[[^\]]*\]\((\/[^)\s]+)\)/)?.[1] ?? null;
}

function parseMeta(
  slug: string,
  data: Record<string, unknown>,
  content: string,
): PostMeta {
  const title = String(data.title ?? slug);
  const description = String(data.description ?? "");
  return {
    slug,
    title,
    description,
    metaTitle: String(data.metaTitle ?? title),
    metaDescription: String(data.metaDescription ?? description),
    image: firstImage(content),
    date: String(data.date ?? ""),
    tags: Array.isArray(data.tags) ? data.tags.map(String) : [],
  };
}

export function listPosts(): PostMeta[] {
  if (!fs.existsSync(postsDir)) return [];
  return fs
    .readdirSync(postsDir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const slug = f.replace(/\.md$/, "");
      const raw = fs.readFileSync(path.join(postsDir, f), "utf8");
      const { data, content } = matter(raw);
      return parseMeta(slug, data, content);
    })
    .sort((a, b) => b.date.localeCompare(a.date));
}

export const CASE_STUDY_TAG = "case-study";

export function listCaseStudies(): PostMeta[] {
  return listPosts().filter((post) => post.tags.includes(CASE_STUDY_TAG));
}

export async function getPost(slug: string): Promise<Post | null> {
  const file = path.join(postsDir, `${slug}.md`);
  if (!path.resolve(file).startsWith(postsDir) || !fs.existsSync(file)) {
    return null;
  }
  const raw = fs.readFileSync(file, "utf8");
  const { data, content } = matter(raw);
  return { ...parseMeta(slug, data, content), html: await renderMarkdown(content) };
}

export async function renderMarkdown(content: string): Promise<string> {
  const html = await unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeSlug)
    .use(rehypeImageDimensions)
    .use(rehypeStringify)
    .process(content);
  return String(html);
}

export function getAdjacentPosts(slug: string): {
  prev: PostMeta | null;
  next: PostMeta | null;
} {
  const posts = listPosts();
  const index = posts.findIndex((p) => p.slug === slug);
  if (index === -1) return { prev: null, next: null };
  return {
    // posts are sorted newest-first: "next" is the newer post, "prev" the older
    next: index > 0 ? posts[index - 1] : null,
    prev: index < posts.length - 1 ? posts[index + 1] : null,
  };
}

export function getRelatedPosts(slug: string, limit = 3): PostMeta[] {
  const posts = listPosts();
  const current = posts.find((p) => p.slug === slug);
  if (!current) return [];
  return posts
    .filter((p) => p.slug !== slug)
    .map((post) => ({
      post,
      shared: post.tags.filter((t) => current.tags.includes(t)).length,
    }))
    .sort(
      (a, b) =>
        b.shared - a.shared || b.post.date.localeCompare(a.post.date),
    )
    .slice(0, limit)
    .map(({ post }) => post);
}

export function formatDate(date: string): string {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}
