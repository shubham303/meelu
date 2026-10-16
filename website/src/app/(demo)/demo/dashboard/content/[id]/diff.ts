import { diffLines, diffWords } from "diff";

export interface Hunk {
  id: number;
  before: string;
  after: string;
  decision: "pending" | "keep" | "discard";
}

export interface Segment {
  kind: "same" | "hunk";
  text?: string;
  hunk?: Hunk;
}

export interface Proposal {
  base: string;
  note: string;
  segments: Segment[];
}

export function buildProposal(base: string, next: string, note: string): Proposal | null {
  const parts = diffLines(base, next);
  const segments: Segment[] = [];
  let id = 0;
  let removed = "";
  let added = "";
  let hasChange = false;
  const flush = () => {
    if (!removed && !added) return;
    segments.push({
      kind: "hunk",
      hunk: { id: id++, before: removed, after: added, decision: "pending" },
    });
    hasChange = true;
    removed = "";
    added = "";
  };
  for (const part of parts) {
    if (part.removed) removed += part.value;
    else if (part.added) added += part.value;
    else {
      flush();
      segments.push({ kind: "same", text: part.value });
    }
  }
  flush();
  if (!hasChange) return null;
  return { base, note, segments };
}

export function decide(proposal: Proposal, hunkId: number, decision: Hunk["decision"]): Proposal {
  return {
    ...proposal,
    segments: proposal.segments.map((s) =>
      s.kind === "hunk" && s.hunk && s.hunk.id === hunkId
        ? { ...s, hunk: { ...s.hunk, decision } }
        : s,
    ),
  };
}

export function decideAll(proposal: Proposal, decision: Hunk["decision"]): Proposal {
  return {
    ...proposal,
    segments: proposal.segments.map((s) =>
      s.kind === "hunk" && s.hunk ? { ...s, hunk: { ...s.hunk, decision } } : s,
    ),
  };
}

export function pendingCount(proposal: Proposal): number {
  return proposal.segments.filter((s) => s.kind === "hunk" && s.hunk?.decision === "pending").length;
}

export function resolve(proposal: Proposal): string {
  return proposal.segments
    .map((s) => {
      if (s.kind === "same") return s.text ?? "";
      const hunk = s.hunk!;
      return hunk.decision === "keep" ? hunk.after : hunk.before;
    })
    .join("");
}

export function wordDiff(before: string, after: string): Array<{ kind: "same" | "del" | "ins"; text: string }> {
  return diffWords(before, after).map((p) => ({
    kind: p.added ? "ins" : p.removed ? "del" : "same",
    text: p.value,
  }));
}
