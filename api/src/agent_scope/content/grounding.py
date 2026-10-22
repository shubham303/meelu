TABLES_NOTE = """The site's pages and the search data are not in this prompt. They arrive when you call add_desk with `site`: the load returns the crawled pages, the Search Console data and their data rules. Load it before you draft, and skip it if it is already loaded. You only read its data here; its writes are not part of this task."""

PAGE_SHAPE = """## The shape of a piece
Every piece is one web page for this site. Nothing else is written here, and Meelu never publishes it: the user puts it on the site, by hand or from a draft the CMS desk saved when they asked.
- **title**: the SEO title tag. Under 60 characters, target keyword near the front.
- **h1**: the headline on the page. It can differ from the title and holds the target keyword.
- **metaDescription**: 140–160 characters. States what the reader gets and holds the keyword.
- **slug**: a short lowercase, hyphenated path that fits the site's existing URL folders, such as /blog/espresso-grind-size.
- **targetKeyword**: the ONE query this page is written to win.
- **bodyMarkdown**: starts after the H1, so it never has a `# ` line. The first paragraph answers the search intent and uses the keyword. H2/H3 sections, short paragraphs, lists only where the content is a list. Internal links are root-relative paths to crawled pages, written as markdown links inside the sentences that mention them. The body is only the page the reader sees: never a metadata block, a list of links to add, or notes to the editor. One call to action at the end, pointing at the page on the site that sells what the piece is about. When markdown cannot express something the page needs, such as a table, a comparison grid or a video embed, write it as a block of plain HTML on its own lines, separated from the text by blank lines; it is kept exactly as written. Never put a script or a style block in the body."""

RESEARCH = """## Research before you write
- **Keyword, from Search Console.** Find the query this page should win in the Search Console queries the Site desk carries. Prefer a query with real demand that no page on the site already ranks for. If an existing page already ranks for it, say so and suggest editing that page instead; writing a second page on the same query splits it.
- **Internal links, from the Site desk.** Pick three to six crawled pages the reader would follow: the product or service page the piece supports, the hub it belongs under, and closely related articles. Use their page types and their passages to judge the fit. Every internal link must be a URL that exists in the crawl. Never invent one. Anchor text says what the target page is.
- **Voice, from the Site desk.** Read two or three of the most-linked pages for format, length and tone, and follow the URL folders for the slug.
- Every claim must trace to the site or to the user. If it is neither, cut it or ask. If no crawl or no search data exists yet, say so and name what the piece is missing because of it."""
