import assert from "node:assert/strict";
import { test } from "node:test";
import { extract } from "../src/main/crawler/extract.js";

const URL = "https://example.com/blog/welcome-email";

const HTML = `<!doctype html><html><head><title>Welcome</title>
<script type="application/ld+json">{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
 {"@type":"ListItem","position":1,"item":{"@id":"https://example.com/","name":"Home"}},
 {"@type":"ListItem","position":2,"item":{"@id":"https://example.com/blog","name":"Blog"}}]}</script>
</head><body>
<header><a href="/">Logo</a><div class="main-nav"><a href="/pricing">Pricing</a><a href="/blog">Blog</a></div></header>
<div class="crumbs"><a href="/">Home</a> › <a href="/blog">Blog</a></div>
<main>
 <h1>Writing a welcome email</h1>
 <p>Short intro. Segment your audience first: <a href="/features/segmentation">segmentation</a> lets you send different emails. Then write the copy.</p>
 <p>See the <a href="/blog/welcome-sequence">sequence guide</a> and the <a href="/blog/welcome-sequence">same guide again</a>.</p>
 <ul><li>Read <a href="https://other.example.org/x" rel="nofollow">this external thing</a>.</li></ul>
 <aside class="sidebar"><a href="/blog/related">Related post</a></aside>
 <nav class="pagination"><a href="/blog?page=2">2</a></nav>
 <a href="/blog/next-post" rel="next">Next</a>
</main>
<footer><a href="/pricing">Pricing</a><a href="/privacy">Privacy</a></footer>
</body></html>`;

function byKey(links) {
  return Object.fromEntries(links.map((l) => [`${l.region} ${l.url}`, l]));
}

test("links carry region, ordinal, context and count", () => {
  const f = extract(HTML, URL, 200);
  const l = byKey(f.outLinks);

  assert.equal(l["header https://example.com/"].anchor, "Logo");
  assert.equal(l["nav https://example.com/pricing"].anchor, "Pricing");
  assert.equal(l["footer https://example.com/pricing"].anchor, "Pricing");
  assert.equal(l["footer https://example.com/privacy"].count, 1);

  assert.equal(l["breadcrumb https://example.com/"].anchor, "Home");
  assert.equal(l["breadcrumb https://example.com/blog"].anchor, "Blog");
  assert.equal(l["nav https://example.com/blog"].anchor, "Blog");

  const seg = l["body https://example.com/features/segmentation"];
  assert.equal(seg.ordinal, 1);
  assert.equal(seg.context, "Short intro. Segment your audience first: segmentation lets you send different emails. Then write the copy.");
  assert.equal(seg.count, 1);

  const seq = l["body https://example.com/blog/welcome-sequence"];
  assert.equal(seq.count, 2);
  assert.equal(seq.anchor, "sequence guide");
  assert.equal(seq.ordinal, 2);

  assert.equal(l["aside https://example.com/blog/related"].region, "aside");
  assert.equal(l["pagination https://example.com/blog?page=2"].region, "pagination");
  assert.equal(l["pagination https://example.com/blog/next-post"].rel, "next");

  assert.equal(f.externalLinks.length, 1);
  assert.equal(f.externalLinks[0].region, "body");
  assert.equal(f.externalLinks[0].rel, "nofollow");
  assert.equal(f.bodyText.split("\n")[1], "Short intro. Segment your audience first: segmentation lets you send different emails. Then write the copy.");
});

test("unmarked template links outside main split into header and footer", () => {
  const html = `<html><body><div><a href="/a">A</a></div><main><p>Hi <a href="/b">B</a></p></main><div><a href="/c">C</a></div></body></html>`;
  const l = byKey(extract(html, "https://example.com/", 200).outLinks);
  assert.equal(l["header https://example.com/a"].region, "header");
  assert.equal(l["body https://example.com/b"].ordinal, 0);
  assert.equal(l["footer https://example.com/c"].region, "footer");
});

test("a page without main treats unmarked links as body", () => {
  const html = `<html><body><div><p>Text <a href="/a">A</a> here.</p></div></body></html>`;
  const [a] = extract(html, "https://example.com/", 200).outLinks;
  assert.equal(a.region, "body");
  assert.equal(a.ordinal, 0);
  assert.equal(a.context, "Text A here.");
});

test("context on a long block is cut at sentence boundaries around the anchor", () => {
  const filler = "This sentence is padding that goes on for a while to push the length up. ".repeat(6);
  const html = `<html><body><main><p>${filler}The link to <a href="/target">the target</a> sits here. ${filler}</p></main></body></html>`;
  const [a] = extract(html, "https://example.com/", 200).outLinks;
  assert.equal(a.context, "The link to the target sits here.");
});
