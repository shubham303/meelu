import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { renderMarkdown } from "@/lib/blog";

export type ComparisonFaq = { question: string; answer: string };

export type ComparisonMeta = {
  slug: string;
  competitor: string;
  competitorUrl: string;
  category: string;
  title: string;
  description: string;
  metaTitle: string;
  metaDescription: string;
  summary: string;
  date: string;
  checked: string;
  faq: ComparisonFaq[];
};

export type Comparison = ComparisonMeta & { html: string };

const comparisonsDir = path.join(process.cwd(), "content", "alternatives");

function parseMeta(slug: string, data: Record<string, unknown>): ComparisonMeta {
  const title = String(data.title ?? slug);
  const description = String(data.description ?? "");
  return {
    slug,
    competitor: String(data.competitor ?? slug),
    competitorUrl: String(data.competitorUrl ?? ""),
    category: String(data.category ?? ""),
    title,
    description,
    metaTitle: String(data.metaTitle ?? title),
    metaDescription: String(data.metaDescription ?? description),
    summary: String(data.summary ?? description),
    date: String(data.date ?? ""),
    checked: String(data.checked ?? data.date ?? ""),
    faq: Array.isArray(data.faq)
      ? data.faq.map((item: Record<string, unknown>) => ({
          question: String(item.question ?? ""),
          answer: String(item.answer ?? ""),
        }))
      : [],
  };
}

export function listComparisons(): ComparisonMeta[] {
  if (!fs.existsSync(comparisonsDir)) return [];
  return fs
    .readdirSync(comparisonsDir)
    .filter((f) => f.endsWith(".md"))
    .map((f) => {
      const slug = f.replace(/\.md$/, "");
      const { data } = matter(fs.readFileSync(path.join(comparisonsDir, f), "utf8"));
      return parseMeta(slug, data);
    })
    .sort((a, b) => a.competitor.localeCompare(b.competitor));
}

export async function getComparison(slug: string): Promise<Comparison | null> {
  const file = path.join(comparisonsDir, `${slug}.md`);
  if (!path.resolve(file).startsWith(comparisonsDir) || !fs.existsSync(file)) return null;
  const { data, content } = matter(fs.readFileSync(file, "utf8"));
  return { ...parseMeta(slug, data), html: await renderMarkdown(content) };
}
