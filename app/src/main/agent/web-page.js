import { createSdkMcpServer, tool as sdkTool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { loadRobots } from "../crawler/fetch.js";
import { extract } from "../crawler/extract.js";
import { isPublicWebUrl } from "../public-address.js";
import { closeWindow, renderPage } from "../render/page.js";

export const WEB_PAGE_SERVER = "webpage";

const READ_WEB_PAGE = "read_web_page";
const OUR_AGENT = "MeeluSEO";
const BODY_WORDS = 1000;

function text(value) {
  return { content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value) }] };
}

export function firstWords(body, limit) {
  const words = body.split(/\s+/).filter(Boolean);
  if (words.length <= limit) return { bodyText: body, truncated: false };
  let seen = 0;
  const lines = [];
  for (const line of body.split("\n")) {
    const count = line.split(/\s+/).filter(Boolean).length;
    if (seen + count > limit) {
      const rest = line.split(/\s+/).filter(Boolean).slice(0, limit - seen);
      if (rest.length) lines.push(rest.join(" "));
      break;
    }
    lines.push(line);
    seen += count;
  }
  return { bodyText: lines.join("\n"), truncated: true };
}

export async function readWebPage(url) {
  if (!(await isPublicWebUrl(url))) {
    return "Only public http(s) pages can be read; that address is local, private or not a web URL.";
  }
  const origin = new URL(url).origin;
  const { robots, body: robotsTxt } = await loadRobots(origin);
  if (robots && robots.isAllowed(url, OUR_AGENT) === false) {
    return `${origin}/robots.txt disallows crawlers from this page, so it was not read.`;
  }

  const rendered = await renderPage({ url, device: "desktop", profile: "generic", robotsTxt });
  void closeWindow();
  if (!rendered.ok) return `The page could not be loaded: ${rendered.error}`;
  if (rendered.status && rendered.status >= 400) {
    return `The site answered HTTP ${rendered.status}, so there is no page content to read.`;
  }

  const facts = extract(rendered.html, rendered.finalUrl, rendered.status);
  const { bodyText, truncated } = firstWords(facts.bodyText, BODY_WORDS);
  return {
    url,
    finalUrl: rendered.finalUrl,
    status: rendered.status,
    title: facts.title,
    metaDescription: facts.metaDescription,
    h1: facts.h1,
    headings: facts.headings.map((h) => ({ level: h.level, text: h.text })),
    wordCount: facts.wordCount,
    bodyText,
    truncated,
    canonical: facts.canonical,
    robotsDirectives: facts.robotsDirectives,
    lang: facts.lang,
    schemaTypes: facts.schemaTypes,
    author: facts.author,
    publishedAt: facts.publishedAt,
    modifiedAt: facts.modifiedAt,
    internalLinks: new Set(facts.outLinks.map((l) => l.url)).size,
    externalLinks: new Set(facts.externalLinks.map((l) => l.url)).size,
    images: facts.images.length,
    imagesWithoutAlt: facts.images.filter((i) => !i.alt).length,
  };
}

export function webPageMcpServer(names) {
  if (!(names ?? []).includes(READ_WEB_PAGE)) return null;
  const readTool = sdkTool(
    READ_WEB_PAGE,
    `Load any public web page in a browser, scripts included, and return what a crawl records for a page: title, meta description, headings, word count, schema, dates, link counts and the first ${BODY_WORDS} words of its text. Pages the site's robots.txt disallows are not read.`,
    { url: z.string().describe("Full http(s) address of the page") },
    async ({ url }) => {
      try {
        return text(await readWebPage(url));
      } catch (e) {
        return text(`The page could not be read: ${e instanceof Error ? e.message : String(e)}`);
      }
    },
  );
  return {
    server: createSdkMcpServer({ name: WEB_PAGE_SERVER, version: "1.0.0", tools: [readTool] }),
    allowed: new Set([READ_WEB_PAGE]),
  };
}
