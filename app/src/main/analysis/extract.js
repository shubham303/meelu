import { query } from "@anthropic-ai/claude-agent-sdk";
import { llmEnv, resolveLlm } from "../agent/runner.js";

const MAX_BODY_CHARS = 24000;

const SYSTEM = `You extract structured facts from one web page for a site knowledge base.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"topics":[{"topic":"...","section":"..."}],"keywords":["..."],"questionsAnswered":["..."]}

Extract only what is unique to THIS page: the subject matter its own body explains in depth. A page that lists, links to or teases other pages (a blog index, a category page, a hub, a nav menu, a "related posts" block, a footer) is describing those pages, not itself — a link title, card summary or excerpt is that other page's information. Skip it entirely: do not turn linked pages into topics, do not lift their keywords, and do not list the questions they answer. For such a listing page, the topics are what the listing itself is about (e.g. one topic naming the collection), the keywords are the few that describe the collection, and questionsAnswered are only the questions the listing itself answers.

- topics: the distinct topics this page's own content covers in substance — usually one to a handful. "section" names the heading the topic sits under (null when the whole page carries it). Topics are short noun phrases, specific enough to tell two pages apart.
- keywords: the few keywords and phrases that best describe this page's own content — multi-word phrases welcome, typically 3–10, never a dump of every term mentioned.
- questionsAnswered: the questions this page's own text actually answers, each phrased the way a person would ask it.

Empty arrays are valid. Never invent topics the text does not support, and prefer fewer precise entries over many loose ones.`;

function pagePrompt(page) {
  const headings = Array.isArray(page.headings)
    ? page.headings
        .map((h) => (h && typeof h === "object" ? `${"#".repeat(h.level ?? 2)} ${h.text ?? ""}` : String(h)))
        .join("\n")
    : "";
  const body = String(page.bodyText ?? "").slice(0, MAX_BODY_CHARS);
  return [
    `URL: ${page.url}`,
    page.title ? `Title: ${page.title}` : "",
    page.metaDescription ? `Meta description: ${page.metaDescription}` : "",
    headings ? `Headings:\n${headings}` : "",
    `Body text:\n${body}`,
  ]
    .filter(Boolean)
    .join("\n\n");
}

function parseExtraction(text) {
  const raw = String(text ?? "").trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("The model returned no JSON object.");
  const parsed = JSON.parse(raw.slice(start, end + 1));
  const topics = (Array.isArray(parsed.topics) ? parsed.topics : [])
    .map((t) =>
      typeof t === "string"
        ? { topic: t.trim(), section: null }
        : {
            topic: String(t?.topic ?? "").trim(),
            section:
              typeof t?.section === "string" && t.section.trim() !== "" ? t.section.trim() : null,
          },
    )
    .filter((t) => t.topic !== "");
  const strings = (v) =>
    (Array.isArray(v) ? v : []).map((s) => String(s ?? "").trim()).filter(Boolean);
  return {
    topics,
    keywords: strings(parsed.keywords),
    questionsAnswered: strings(parsed.questionsAnswered),
  };
}

export async function extractPage(page, llm) {
  const { gateway, model, anthropicKey, limits } = await resolveLlm(llm);

  const q = query({
    prompt: pagePrompt(page),
    options: {
      model,
      systemPrompt: SYSTEM,
      tools: [],
      allowedTools: [],
      permissionMode: "default",
      settingSources: [],
      maxTurns: 1,
      env: llmEnv(gateway, anthropicKey, limits),
    },
  });

  let output = null;
  for await (const m of q) {
    if (m.type === "result") {
      if (m.subtype !== "success" || m.is_error) {
        throw new Error(m.result || m.subtype || "The extraction run failed.");
      }
      output = m.result;
    }
  }
  if (output === null) throw new Error("The extraction run produced no result.");
  return { ...parseExtraction(output), model };
}
