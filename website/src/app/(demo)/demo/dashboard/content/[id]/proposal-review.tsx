"use client";

import { Sparkles } from "lucide-react";
import { Button } from "@demo/components/ui";
import { cn } from "@demo/lib/utils";
import { decide, decideAll, pendingCount, wordDiff, type Hunk, type Proposal } from "./diff";

export function ProposalReview({
  proposal,
  onChange,
  onDone,
}: {
  proposal: Proposal;
  onChange: (next: Proposal) => void;
  onDone: (next: Proposal) => void;
}) {
  const pending = pendingCount(proposal);
  const hunks = proposal.segments.filter((s) => s.kind === "hunk").length;
  const settle = (next: Proposal) => {
    if (pendingCount(next) === 0) onDone(next);
    else onChange(next);
  };

  return (
    <div>
      <div className="sticky top-0 z-10 -mx-2 mb-6 flex items-center justify-between rounded-lg bg-bg/95 px-2 py-2.5 backdrop-blur">
        <div className="flex items-center gap-2 text-sm text-ink">
          <Sparkles size={14} className="text-accent" />
          <span>
            {hunks} change{hunks === 1 ? "" : "s"} proposed
            {proposal.note ? <span className="text-sub"> · {proposal.note}</span> : null}
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => settle(decideAll(proposal, "discard"))}>
            Discard all
          </Button>
          <Button size="sm" onClick={() => settle(decideAll(proposal, "keep"))}>
            Keep {pending === hunks ? "all" : "the rest"}
          </Button>
        </div>
      </div>

      <div className="piece-doc-diff whitespace-pre-wrap text-[17px] leading-[1.7] text-ink">
        {proposal.segments.map((s, i) =>
          s.kind === "same" ? (
            <span key={i}>{s.text}</span>
          ) : (
            <HunkView key={i} hunk={s.hunk!} onDecide={(d) => settle(decide(proposal, s.hunk!.id, d))} />
          ),
        )}
      </div>
    </div>
  );
}

function HunkView({ hunk, onDecide }: { hunk: Hunk; onDecide: (d: Hunk["decision"]) => void }) {
  if (hunk.decision === "keep") return <span>{hunk.after}</span>;
  if (hunk.decision === "discard") return <span>{hunk.before}</span>;
  const parts = wordDiff(hunk.before, hunk.after);
  return (
    <span className="inline">
      {parts.map((p, i) =>
        p.kind === "same" ? (
          <span key={i}>{p.text}</span>
        ) : (
          <span
            key={i}
            className={cn(
              "rounded-[3px] px-0.5",
              p.kind === "del" ? "bg-bad/10 text-bad line-through" : "bg-good/10 text-good",
            )}
          >
            {p.text}
          </span>
        ),
      )}
      <span className="my-2 flex items-center justify-end gap-1.5 whitespace-normal text-[13px]">
        <button
          type="button"
          onClick={() => onDecide("discard")}
          className="rounded-md px-2 py-1 text-sub transition-colors hover:bg-panel2 hover:text-ink cursor-pointer"
        >
          Discard
        </button>
        <button
          type="button"
          onClick={() => onDecide("keep")}
          className="rounded-md border border-edge2 bg-panel px-2 py-1 text-ink transition-colors hover:bg-panel2 cursor-pointer"
        >
          Keep
        </button>
      </span>
    </span>
  );
}
