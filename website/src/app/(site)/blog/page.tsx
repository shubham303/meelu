import type { Metadata } from "next";
import Link from "next/link";
import { listPosts, formatDate } from "@/lib/blog";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Blog — AI data analysis, SEO and building Meelu",
  description:
    "Notes from building Meelu in the open: analyzing real data with AI, technical SEO, MCP servers, and building a marketing agent that suggests while you decide.",
  alternates: { canonical: `${site.url}/blog` },
};

export default function BlogIndex() {
  const posts = listPosts();

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-20">
      <p className="text-xs font-medium uppercase tracking-widest text-faint">
        Blog
      </p>
      <h1 className="mt-3 font-display text-3xl tracking-tight text-ink sm:text-4xl">
        Notes from building Meelu in the open.
      </h1>

      <div className="mt-12 flex flex-col gap-5">
        {posts.map((post) => (
          <article
            key={post.slug}
            className="rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-edge2"
          >
            <time className="font-mono text-xs text-faint">
              {formatDate(post.date)}
            </time>
            <h2 className="mt-2 text-lg font-medium leading-snug text-ink">
              <Link
                href={`/blog/${post.slug}`}
                className="transition-colors hover:text-accent"
              >
                {post.title}
              </Link>
            </h2>
            <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-sub">
              {post.description}
            </p>
          </article>
        ))}
        {posts.length === 0 && <p className="text-sub">Nothing here yet.</p>}
      </div>
    </div>
  );
}
