"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface RunOutcome {
  stopped: boolean;
  found: number;
  shortlisted: number;
  kept: number;
  failed: string[];
  problems: string[];
}

function Notice({
  tone = "neutral",
  title,
  hint,
  action,
  onDismiss,
}: {
  tone?: "neutral" | "good" | "warn" | "bad";
  title: string;
  hint?: string | null;
  action?: ReactNode;
  onDismiss?: () => void;
}) {
  const tones = {
    neutral: "border-edge bg-panel",
    good: "border-good/30 bg-good/5",
    warn: "border-warn/30 bg-warn/5",
    bad: "border-bad/30 bg-bad/5",
  };
  const titleTone = { neutral: "text-ink", good: "text-good", warn: "text-warn", bad: "text-bad" };
  return (
    <div
      role={tone === "bad" || tone === "warn" ? "alert" : "status"}
      className={cn("flex flex-wrap items-center gap-3 rounded-[14px] border px-4 py-3", tones[tone])}
    >
      <div className="min-w-0 flex-1 space-y-0.5">
        <p className={cn("text-sm font-semibold", titleTone[tone])}>{title}</p>
        {hint && <p className="text-[13px] text-sub">{hint}</p>}
      </div>
      {action}
      {onDismiss && (
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="cursor-pointer rounded-md p-1 text-faint hover:text-ink"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}

const linkCls =
  "inline-flex items-center rounded-lg border border-edge2 bg-panel px-3.5 py-2 text-[13.5px] font-medium text-ink hover:bg-panel2";

export function RunError({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  if (/credit balance/i.test(message)) {
    return (
      <Notice
        tone="warn"
        title={message}
        hint="Searches and profile checks are paid from credits."
        action={
          <Link href="/dashboard/credits" className={linkCls}>
            Add credits
          </Link>
        }
        onDismiss={onDismiss}
      />
    );
  }
  if (/still going|already going/i.test(message)) {
    return (
      <Notice
        title="A lead search is already running on another site."
        hint="One run at a time per account. This one can start when that run finishes."
        onDismiss={onDismiss}
      />
    );
  }
  return <Notice tone="bad" title={message} onDismiss={onDismiss} />;
}

export function RunResult({
  outcome,
  onEditBriefs,
  onDismiss,
}: {
  outcome: RunOutcome;
  onEditBriefs: () => void;
  onDismiss: () => void;
}) {
  const failures = outcome.failed.map((label) => (
    <Notice
      key={label}
      tone="bad"
      title={`${label} failed this run.`}
      hint={`The other sources finished; ${outcome.kept} ${outcome.kept === 1 ? "lead" : "leads"} came from them. ${label} will be tried again next run.`}
    />
  ));

  let main: ReactNode;
  if (outcome.stopped) {
    main = (
      <Notice
        title="You stopped the run."
        hint={`${outcome.kept} ${outcome.kept === 1 ? "person" : "people"} it had already checked ${outcome.kept === 1 ? "is" : "are"} in New. The ones it hadn't reached yet can come up again next run.`}
        onDismiss={onDismiss}
      />
    );
  } else if (outcome.kept > 0) {
    main = (
      <Notice
        tone="good"
        title={`Run finished: ${outcome.kept} ${outcome.kept === 1 ? "person" : "people"} worth contacting.`}
        onDismiss={onDismiss}
      />
    );
  } else if (outcome.found > 0) {
    main = (
      <Notice
        title={`This run found ${outcome.found} people, but none were worth contacting.`}
        hint="Try naming what your people complain about, or turn on another source."
        action={
          <button type="button" onClick={onEditBriefs} className={cn(linkCls, "cursor-pointer")}>
            Edit briefs
          </button>
        }
        onDismiss={onDismiss}
      />
    );
  } else {
    main = (
      <Notice
        title="This run found nobody new."
        hint="Everyone it came across has already been shown to you or set aside. Describe the people more broadly, or turn on another source."
        onDismiss={onDismiss}
      />
    );
  }

  return (
    <div className="space-y-2.5">
      {main}
      {failures}
      {outcome.problems.length > 0 && (
        <Notice
          tone="bad"
          title="Some people were not checked this run."
          hint={`${outcome.problems.join(" · ")} They stay in the queue and are checked again next run.`}
        />
      )}
    </div>
  );
}
