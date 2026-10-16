import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocsBody, DocsDescription, DocsPage, DocsTitle } from "fumadocs-ui/layouts/docs/page";
import { createRelativeLink } from "fumadocs-ui/mdx";
import { getDocsMdxComponents } from "@/components/docs-mdx";
import { docsSource } from "@/lib/docs-source";

export default async function DocsRoute({ params }: PageProps<"/docs/[[...slug]]">) {
  const { slug } = await params;
  const page = docsSource.getPage(slug);
  if (!page) notFound();

  const Body = page.data.body;

  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      <DocsTitle className="font-display font-medium tracking-tight">{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <Body components={getDocsMdxComponents({ a: createRelativeLink(docsSource, page) })} />
      </DocsBody>
    </DocsPage>
  );
}

export function generateStaticParams() {
  return docsSource.generateParams();
}

export async function generateMetadata({ params }: PageProps<"/docs/[[...slug]]">): Promise<Metadata> {
  const { slug } = await params;
  const page = docsSource.getPage(slug);
  if (!page) notFound();

  return {
    title: slug ? `${page.data.title} — Docs` : "Docs",
    description: page.data.description,
    alternates: { canonical: page.url },
  };
}
