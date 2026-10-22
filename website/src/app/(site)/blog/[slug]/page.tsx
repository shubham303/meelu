import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getPost,
  listPosts,
  formatDate,
  getAdjacentPosts,
  getRelatedPosts,
} from "@/lib/blog";
import { site } from "@/lib/site";

export function generateStaticParams() {
  return listPosts().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/blog/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return {};
  const url = `${site.url}/blog/${post.slug}`;
  return {
    // Articles carry their own name; the " · Meelu" suffix only pushes the title past
    // what a result shows.
    title: { absolute: post.metaTitle },
    description: post.metaDescription,
    alternates: { canonical: url },
    openGraph: {
      title: post.metaTitle,
      description: post.metaDescription,
      type: "article",
      publishedTime: post.date,
      url,
      ...(post.image ? { images: [post.image] } : {}),
    },
  };
}

export default async function BlogPost({ params }: PageProps<"/blog/[slug]">) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();

  const { prev, next } = getAdjacentPosts(slug);
  const related = getRelatedPosts(slug);

  return (
    <article className="mx-auto w-full max-w-3xl px-6 py-20">
      <Link
        href="/blog"
        className="font-mono text-xs text-faint transition-colors hover:text-accent"
      >
        ← All posts
      </Link>
      <header className="mt-6">
        <time className="font-mono text-xs text-faint">
          {formatDate(post.date)}
        </time>
        <h1 className="mt-2 font-display text-3xl leading-[1.15] tracking-tight text-ink text-balance sm:text-4xl">
          {post.title}
        </h1>
        <p className="mt-4 text-lg text-sub text-pretty">{post.description}</p>
      </header>
      <div
        className="prose mt-10 max-w-none prose-headings:font-display prose-headings:tracking-tight prose-headings:text-ink prose-p:text-ink/90 prose-a:text-accent prose-strong:text-ink prose-li:text-ink/90 prose-img:rounded-xl prose-img:border prose-img:border-edge prose-img:bg-panel prose-code:text-ink prose-pre:border prose-pre:border-edge prose-pre:bg-panel prose-pre:text-ink prose-blockquote:border-l-accent prose-blockquote:text-sub prose-th:text-ink prose-td:text-ink/90 [&_[data-meelu-html]]:my-8 [&_[data-meelu-html]_svg]:h-auto [&_[data-meelu-html]_svg]:w-full"
        dangerouslySetInnerHTML={{ __html: post.html }}
      />

      <div className="mt-14 rounded-2xl border border-edge bg-panel p-6">
        <p className="text-sm leading-relaxed text-sub">
          This post is part of building{" "}
          <Link
            href="/"
            className="font-medium text-accent transition-colors hover:text-accent-hi"
          >
            Meelu, an AI assistant for digital marketing
          </Link>{" "}
          — site audits, keyword clusters, web page drafts, data analysis and
          social listening, with you approving every change.{" "}
          <Link
            href="/download"
            className="font-medium text-accent transition-colors hover:text-accent-hi"
          >
            Download the app
          </Link>{" "}
          to run it on your own site.
        </p>
      </div>

      {related.length > 0 && (
        <section className="mt-14">
          <p className="text-xs font-medium uppercase tracking-widest text-faint">
            Related posts
          </p>
          <div className="mt-4 flex flex-col gap-4">
            {related.map((rel) => (
              <article
                key={rel.slug}
                className="rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
              >
                <time className="font-mono text-xs text-faint">
                  {formatDate(rel.date)}
                </time>
                <h2 className="mt-1 text-base font-medium leading-snug text-ink">
                  <Link
                    href={`/blog/${rel.slug}`}
                    className="transition-colors hover:text-accent"
                  >
                    {rel.title}
                  </Link>
                </h2>
              </article>
            ))}
          </div>
        </section>
      )}

      {(prev || next) && (
        <nav
          aria-label="Adjacent posts"
          className="mt-14 flex flex-col gap-4 border-t border-edge pt-8 sm:flex-row sm:justify-between"
        >
          {prev ? (
            <Link
              href={`/blog/${prev.slug}`}
              className="group max-w-xs"
            >
              <span className="font-mono text-xs text-faint">← Older</span>
              <span className="mt-1 block text-sm font-medium leading-snug text-ink transition-colors group-hover:text-accent">
                {prev.title}
              </span>
            </Link>
          ) : (
            <span />
          )}
          {next ? (
            <Link
              href={`/blog/${next.slug}`}
              className="group max-w-xs sm:text-right"
            >
              <span className="font-mono text-xs text-faint">Newer →</span>
              <span className="mt-1 block text-sm font-medium leading-snug text-ink transition-colors group-hover:text-accent">
                {next.title}
              </span>
            </Link>
          ) : (
            <span />
          )}
        </nav>
      )}

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            headline: post.title,
            description: post.description,
            datePublished: post.date,
            dateModified: post.date,
            url: `${site.url}/blog/${post.slug}`,
            mainEntityOfPage: `${site.url}/blog/${post.slug}`,
            ...(post.image ? { image: `${site.url}${post.image}` } : {}),
            author: {
              "@type": "Person",
              name: site.author.name,
              url: site.author.url,
            },
            publisher: {
              "@type": "Organization",
              name: site.name,
              url: site.url,
              logo: { "@type": "ImageObject", url: `${site.url}/meelu-logo.png` },
            },
          }),
        }}
      />
    </article>
  );
}
