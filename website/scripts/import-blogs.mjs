import fs from "node:fs";
import path from "node:path";

const [, , sourceDir] = process.argv;
if (!sourceDir) {
  console.error("usage: node scripts/import-blogs.mjs <blogs-dir>");
  process.exit(1);
}

const root = process.cwd();
const contentDir = path.join(root, "content", "blog");
const publicDir = path.join(root, "public", "blog");
fs.mkdirSync(contentDir, { recursive: true });

const slugs = fs
  .readdirSync(sourceDir, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => d.name)
  .filter((slug) => fs.existsSync(path.join(sourceDir, slug, "blog.md")));

for (const slug of slugs) {
  let body = fs.readFileSync(path.join(sourceDir, slug, "blog.md"), "utf8");

  const metaMatch = body.match(/<!--\s*meta description:\s*([\s\S]*?)-->/i);
  const description = metaMatch ? metaMatch[1].trim().replace(/\s+/g, " ") : "";
  body = body.replace(/<!--\s*meta description:[\s\S]*?-->\s*/i, "");

  const titleMatch = body.match(/^#\s+(.+)$/m);
  const title = titleMatch ? titleMatch[1].trim() : slug;
  if (titleMatch) body = body.replace(titleMatch[0], "").trimStart();

  body = body.replaceAll("](images/", `](/blog/${slug}/images/`);

  const stat = fs.statSync(path.join(sourceDir, slug, "blog.md"));
  const date = stat.mtime.toISOString().slice(0, 10);

  const frontmatter = [
    "---",
    `title: ${JSON.stringify(title)}`,
    `description: ${JSON.stringify(description)}`,
    `date: "${date}"`,
    'tags: ["meelu-analytics", "data-analysis"]',
    "---",
    "",
  ].join("\n");

  fs.writeFileSync(path.join(contentDir, `${slug}.md`), frontmatter + body);

  const imagesDir = path.join(sourceDir, slug, "images");
  if (fs.existsSync(imagesDir)) {
    fs.cpSync(imagesDir, path.join(publicDir, slug, "images"), {
      recursive: true,
    });
  }
  console.log(`imported ${slug}`);
}
