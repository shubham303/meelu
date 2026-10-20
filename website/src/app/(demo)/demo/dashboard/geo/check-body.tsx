"use client";

import { useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Badge, Button } from "@demo/components/ui";
import type { GeoAiAnswer, GeoCheck } from "@demo/lib/types";
import { cn, formatRelative } from "@demo/lib/utils";
import { INTENT, PLATFORM, POINT, VERDICT, pathOf } from "./lib";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-sub">{title}</h3>
      {children}
    </section>
  );
}

function AnswerBlock({ answer }: { answer: GeoAiAnswer }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="space-y-1.5 rounded-xl border border-edge px-3 py-2.5">
      <div className="flex items-center justify-between gap-2 text-[13px]">
        <span className="font-semibold text-ink">{PLATFORM[answer.platform]}</span>
        {answer.error ? (
          <span className="text-bad">could not fetch</span>
        ) : !answer.shown ? (
          <span className="text-sub">no answer shown</span>
        ) : answer.citedUs ? (
          <span className="font-medium text-good">cites you</span>
        ) : (
          <span className="text-sub">not cited</span>
        )}
      </div>
      {answer.error && <p className="text-[12.5px] text-sub">{answer.error}</p>}
      {answer.shown && (
        <>
          {answer.covers.length > 0 && (
            <p className="text-[13px] text-ink">
              <span className="text-sub">Covers · </span>
              {answer.covers.join(" · ")}
            </p>
          )}
          {answer.misses.length > 0 && (
            <p className="text-[13px] text-ink">
              <span className="text-sub">Misses · </span>
              {answer.misses.join(" · ")}
            </p>
          )}
          {expanded && (
            <div className="space-y-2 pt-1">
              <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink">{answer.text}</p>
              {answer.citations.length > 0 && (
                <ul className="space-y-0.5">
                  {answer.citations.map((c) => (
                    <li key={c.url} className="truncate text-[12.5px]">
                      <a href={c.url} target="_blank" rel="noreferrer" className="text-accent hover:underline">
                        {c.title || c.url}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="cursor-pointer text-[12.5px] font-medium text-accent hover:underline"
          >
            {expanded ? "Hide full answer" : "Read full answer"}
          </button>
        </>
      )}
    </div>
  );
}

export function PrimaryAction({ check }: { check: GeoCheck }) {
  if (check.verdict === "low_rank") {
    return (
      <Link href="/demo/dashboard/seo">
        <Button>Open SEO</Button>
      </Link>
    );
  }
  if (check.pageUrl) {
    return (
      <a href={check.pageUrl} target="_blank" rel="noreferrer">
        <Button>
          Open page <ExternalLink size={13} />
        </Button>
      </a>
    );
  }
  return null;
}

export function CheckBody({ check }: { check: GeoCheck }) {
  const best = check.pages.find((p) => p.pageId === check.pageId);
  const verdict = check.verdict ? VERDICT[check.verdict] : null;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 text-[13px] text-sub">
        {check.intent && <Badge>{INTENT[check.intent]}</Badge>}
        {verdict && <Badge tone={verdict.tone}>{verdict.label}</Badge>}
        <span>Checked {formatRelative(check.finishedAt ?? check.startedAt)}</span>
      </div>

      <div className="space-y-1 rounded-xl bg-panel2 px-3 py-2.5">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-sub">Best page</p>
        {check.pageUrl ? (
          <>
            <a
              href={check.pageUrl}
              target="_blank"
              rel="noreferrer"
              className="block break-all text-[13.5px] text-accent hover:underline"
            >
              {pathOf(check.pageUrl)}
            </a>
            <p className="text-[12.5px] text-sub">
              {check.position != null
                ? `Average position ${check.position.toFixed(1)} in Search Console, last 28 days`
                : "No Search Console impressions in the last 28 days"}
            </p>
          </>
        ) : (
          <p className="text-[13.5px] text-ink">No page on the site answers this question.</p>
        )}
      </div>

      <Section title="What the question needs">
        <ul className="space-y-2">
          {check.requiredPoints.map((point) => {
            const judged = best?.points.find((p) => p.point === point);
            const status = POINT[judged?.status ?? "missing"];
            return (
              <li key={point} className="flex gap-2.5 text-[13.5px]">
                <span className={cn("w-3 shrink-0 font-semibold", status.className)} aria-label={status.label}>
                  {status.mark}
                </span>
                <span className="min-w-0">
                  <span className="text-ink">{point}</span>
                  {judged?.evidence && (
                    <span className="mt-0.5 block text-[12.5px] italic text-sub">“{judged.evidence}”</span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      </Section>

      {check.pageAdds.length > 0 && (
        <Section title="What your page adds">
          <ul className="list-disc space-y-1 pl-5 text-[13.5px] text-ink">
            {check.pageAdds.map((add) => (
              <li key={add}>{add}</li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="AI answers">
        <div className="space-y-2">
          {check.aiAnswers.map((a) => (
            <AnswerBlock key={a.platform} answer={a} />
          ))}
        </div>
      </Section>

      {check.suggestion && (
        <Section title="Suggestion">
          <p className="text-[13.5px] leading-relaxed text-ink">{check.suggestion}</p>
        </Section>
      )}

      {check.pages.length > 1 && (
        <Section title="Other pages checked">
          <ul className="space-y-1 text-[13px]">
            {check.pages
              .filter((p) => p.pageId !== check.pageId)
              .map((p) => (
                <li key={p.pageId} className="flex justify-between gap-3">
                  <a href={p.url} target="_blank" rel="noreferrer" className="truncate text-accent hover:underline">
                    {pathOf(p.url)}
                  </a>
                  <span className="shrink-0 tabular-nums text-sub">{Math.round(p.coverage * 100)}% answered</span>
                </li>
              ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
