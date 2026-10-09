"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { refuseOnWeb, streamTurn, usePinnedSite, type RunningTurn } from "@/components/agent";
import type { PieceForm } from "./use-autosave";

export interface AgentReply {
  text: string;
  body: string | null;
}

export interface PassageRequest {
  instruction: string;
  passage: string;
}

export interface Progress {
  onText?: (full: string) => void;
  onTool?: (name: string) => void;
}

const FENCE = /```(?:markdown|md|mdx)?\s*\n?([\s\S]*?)```/;

export interface FlaggedIssue {
  title: string;
  detail?: string | null;
  anchorText?: string | null;
  suggestion?: string | null;
}

function issuesFraming(issues: FlaggedIssue[]): string[] {
  if (issues.length === 0) return [];
  return [
    "",
    `Open issues flagged by the checks (${issues.length}):`,
    ...issues.map((i, n) =>
      [
        `${n + 1}. ${i.title}`,
        i.detail ? ` — ${i.detail}` : "",
        i.anchorText ? ` Where: """${i.anchorText}"""` : "",
        i.suggestion ? ` Suggested: """${i.suggestion}"""` : "",
      ].join(""),
    ),
  ];
}

export function useAgent(
  pieceId: string,
  getDraft: () => PieceForm | null,
  getIssues: () => FlaggedIssue[] = () => [],
) {
  const siteId = usePinnedSite();
  const runningRef = useRef<RunningTurn | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => () => runningRef.current?.abort(), []);

  const run = useCallback(
    async (message: string, options: Progress = {}): Promise<AgentReply | null> => {
      if (refuseOnWeb("content-draft turn")) return null;
      setError(null);
      setBusy(true);
      const turn = streamTurn({
        action: "content-draft",
        siteId,
        message,
        onText: options.onText ? (_chunk, full) => options.onText?.(full) : undefined,
        onTool: options.onTool,
      });
      runningRef.current = turn;
      const res = await turn.result;
      runningRef.current = null;
      setBusy(false);
      if (!res.ok) {
        setError(res.error ?? "The turn stopped before it answered.");
        return null;
      }
      const fenced = res.text.match(FENCE);
      return {
        text: (fenced ? res.text.replace(fenced[0], "") : res.text).trim(),
        body: fenced ? fenced[1].replace(/\s+$/, "") : null,
      };
    },
    [siteId],
  );

  const draftFraming = useCallback(() => {
    const draft = getDraft();
    return [
      `We are working on ONE web page, id ${pieceId}.`,
      `Title: ${draft?.title || "(empty)"}`,
      `H1: ${draft?.h1 || "(empty)"}`,
      `Meta description: ${draft?.metaDescription || "(empty)"}`,
      `Slug: ${draft?.slug || "(empty)"}`,
      `Target keyword: ${draft?.targetKeyword || "(empty)"}`,
      "Current body of the piece:",
      `"""${draft?.bodyMarkdown ?? ""}"""`,
      ...issuesFraming(getIssues()),
    ].join("\n");
  }, [getDraft, getIssues, pieceId]);

  const rewritePassage = useCallback(
    async (req: PassageRequest, progress: Progress = {}): Promise<string | null> => {
      const out = await run(
        [
          draftFraming(),
          "",
          "This is a passage request. Here is the passage to change:",
          `"""${req.passage}"""`,
          "",
          "Reply with ONLY its replacement — no fence, no quotes, no commentary. Change nothing else.",
          "",
          `Me: ${req.instruction}`,
        ].join("\n"),
        progress,
      );
      if (!out) return null;
      return (out.body ?? out.text).trim() || null;
    },
    [draftFraming, run],
  );

  const stop = useCallback(() => runningRef.current?.abort(), []);

  return { busy, error, rewritePassage, stop };
}
