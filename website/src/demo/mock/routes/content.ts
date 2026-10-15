import type { ContentPiece, ContentPieceSlim } from "@demo/lib/types";
import type { PieceIssue } from "@/app/demo/dashboard/content/types";
import * as content from "../data/content";
import { b, MockHttpError, newId, now, ok, paginate, type Route } from "../core";

const state = {
  pieces: content.PIECES.map((p) => ({ ...p })),
  issues: content.ISSUES.map((i) => ({ ...i })),
};

const ISSUE_STATES = ["open", "fixed", "dismissed"];
const SLUG_RE = /^\/?[a-z0-9]+(?:-[a-z0-9]+)*(?:\/[a-z0-9]+(?:-[a-z0-9]+)*)*\/?$/;

function slim(p: ContentPiece): ContentPieceSlim {
  const { id, siteId, title, slug, targetKeyword, wordCount, checks, mediaSource, mediaUrl, createdAt, updatedAt } = p;
  return { id, siteId, title, slug, targetKeyword, wordCount, checks, mediaSource, mediaUrl, createdAt, updatedAt };
}

function findPiece(id: string): ContentPiece {
  const piece = state.pieces.find((p) => p.id === id);
  if (!piece) throw new MockHttpError(404, "Not found");
  return piece;
}

function oneLine(v: unknown): string {
  return String(v).split(/\s+/).filter(Boolean).join(" ");
}

function cleanSlug(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  const text = String(v).trim().toLowerCase();
  if (!text) return null;
  if (!SLUG_RE.test(text)) {
    throw new MockHttpError(422, "slug must be a URL path of lowercase letters, digits and hyphens, such as /blog/espresso-grind-size.");
  }
  return "/" + text.replace(/^\/+|\/+$/g, "");
}

function cleanKeyword(v: unknown): string | null {
  if (v === null || v === undefined) return null;
  return oneLine(v).toLowerCase() || null;
}

function requiredTitle(v: unknown): string {
  const title = (v === null || v === undefined ? "" : String(v)).trim();
  if (!title) throw new MockHttpError(422, "title is required.");
  return title;
}

function withChecks(p: ContentPiece): ContentPiece {
  return { ...p, wordCount: content.wordCount(p.bodyMarkdown), checks: content.runChecks(p) };
}

function yamlValue(value: string): string {
  return '"' + value.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
}

function markdownExport(p: ContentPiece): string {
  const front: Array<[string, string | null | undefined]> = [
    ["title", p.title],
    ["description", p.metaDescription],
    ["slug", p.slug],
    ["keyword", p.targetKeyword],
  ];
  const header = front.filter(([, v]) => v).map(([k, v]) => `${k}: ${yamlValue(v as string)}`).join("\n");
  const heading = p.h1 ? `# ${p.h1}\n\n` : "";
  return `---\n${header}\n---\n\n${heading}${(p.bodyMarkdown ?? "").trimEnd()}\n`;
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/content\/pieces$/, (_m, q) => {
    let rows = [...state.pieces].sort((a, c) => c.updatedAt.localeCompare(a.updatedAt));
    const needle = q.get("search")?.trim().toLowerCase();
    if (needle) {
      rows = rows.filter((p) =>
        [p.title, p.h1, p.targetKeyword ?? "", p.bodyMarkdown].some((f) => f.toLowerCase().includes(needle)),
      );
    }
    return paginate(rows.map(slim), q);
  }],
  ["POST", /^\/api\/v1\/content\/pieces$/, (_m, _q, body) => {
    const at = now();
    const piece = content.buildPiece({
      id: newId("cp"),
      title: requiredTitle(b(body, "title")),
      h1: b(body, "h1") == null ? "" : oneLine(b(body, "h1")),
      metaDescription: b(body, "metaDescription") == null ? "" : oneLine(b(body, "metaDescription")),
      slug: cleanSlug(b(body, "slug")),
      targetKeyword: cleanKeyword(b(body, "targetKeyword")),
      bodyMarkdown: String(b(body, "bodyMarkdown") ?? ""),
      createdBy: "user",
      createdAt: at,
      updatedAt: at,
      sourcePageId: (b(body, "sourcePageId") as string | null | undefined) ?? null,
    });
    state.pieces.unshift(piece);
    return ok(piece);
  }],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m) => ok(findPiece(m[1]))],
  ["PATCH", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m, _q, body) => {
    const existing = findPiece(m[1]);
    const next: ContentPiece = { ...existing };
    if (body.title != null) next.title = requiredTitle(body.title);
    if (body.h1 != null) next.h1 = oneLine(body.h1);
    if (body.metaDescription != null) next.metaDescription = oneLine(body.metaDescription);
    if (body.bodyMarkdown != null) next.bodyMarkdown = String(body.bodyMarkdown);
    if ("slug" in body) next.slug = cleanSlug(body.slug);
    if ("targetKeyword" in body) next.targetKeyword = cleanKeyword(body.targetKeyword);
    if ("sourcePageId" in body) next.sourcePageId = (body.sourcePageId as string | null) || null;
    const updated = withChecks({ ...next, updatedAt: now() });
    state.pieces = state.pieces.map((p) => (p.id === existing.id ? updated : p));
    return ok(updated);
  }],
  ["DELETE", /^\/api\/v1\/content\/pieces\/([^/]+)$/, (m) => {
    const piece = findPiece(m[1]);
    state.pieces = state.pieces.filter((p) => p.id !== piece.id);
    state.issues = state.issues.filter((i) => i.pieceId !== piece.id);
    return ok({ id: piece.id, deleted: true });
  }],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)\/markdown$/, (m) => markdownExport(findPiece(m[1]))],
  ["GET", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues$/, (m, q) => {
    findPiece(m[1]);
    const issueState = q.get("state");
    const tool = q.get("tool");
    const rows = state.issues.filter(
      (i) => i.pieceId === m[1] && (!issueState || i.state === issueState) && (!tool || i.tool === tool),
    );
    return paginate(rows, q);
  }],
  ["POST", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues$/, (m, _q, body) => {
    findPiece(m[1]);
    const tool = String(b(body, "tool") ?? "").trim();
    if (!tool || tool.length > 40) throw new MockHttpError(422, "tool is required.");
    const rows = (b(body, "issues") as Array<Record<string, unknown>> | undefined) ?? [];
    const runId = newId("run");
    const at = now();
    const created: PieceIssue[] = rows.map((r) => {
      const code = String(r.code ?? "").trim();
      const title = String(r.title ?? "").trim();
      if (!code || !title) throw new MockHttpError(422, "Each issue needs a code and a title.");
      return {
        id: content.nextIssueId(),
        pieceId: m[1],
        tool,
        code,
        title,
        detail: r.detail == null ? null : String(r.detail).trim() || null,
        anchorText: r.anchorText == null ? null : String(r.anchorText) || null,
        suggestion: r.suggestion == null ? null : String(r.suggestion) || null,
        state: "open",
        runId,
        createdAt: at,
        updatedAt: at,
      };
    });
    state.issues = [...state.issues.filter((i) => !(i.pieceId === m[1] && i.tool === tool)), ...created];
    return ok({ runId, tool, issues: created });
  }],
  ["PATCH", /^\/api\/v1\/content\/pieces\/([^/]+)\/issues\/([^/]+)$/, (m, _q, body) => {
    findPiece(m[1]);
    const issueState = b(body, "state");
    if (typeof issueState !== "string" || !ISSUE_STATES.includes(issueState)) {
      throw new MockHttpError(422, `state must be one of ${ISSUE_STATES.join(", ")}.`);
    }
    const issue = state.issues.find((i) => i.id === m[2] && i.pieceId === m[1]);
    if (!issue) throw new MockHttpError(404, "Not found");
    Object.assign(issue, { state: issueState, updatedAt: now() });
    return ok(issue);
  }],
];
