"use client";

import { ExternalLink } from "lucide-react";
import { Badge, Button, Card } from "@demo/components/ui";
import { cn } from "@demo/lib/utils";
import type { Lead, LeadReviewStatus } from "@demo/lib/types";
import { ago, byline, contactLink, daysLeft, platformLabel, shortDate } from "./lib";

function ContactButtons({ lead, compact }: { lead: Lead; compact?: boolean }) {
  const link = contactLink(lead);
  const cls = cn(
    "inline-flex items-center gap-1.5 rounded-lg border border-edge2 font-medium text-ink hover:bg-panel2",
    compact ? "px-2.5 py-1 text-[12.5px]" : "px-3 py-1.5 text-[13px]",
  );
  return (
    <>
      {link && (
        <a href={link.href} target="_blank" rel="noreferrer" className={cls}>
          {compact ? (link.label === "Open post" ? "Post" : "Profile") : link.label}
          <ExternalLink size={compact ? 12 : 13} />
        </a>
      )}
      {lead.email ? (
        <a href={`mailto:${lead.email}`} className={cls}>
          {compact ? "Email" : lead.email}
          {compact && <ExternalLink size={12} />}
        </a>
      ) : (
        !compact && <span className="inline-flex items-center text-[13px] text-sub">No public email</span>
      )}
    </>
  );
}

export function LeadCard({
  lead,
  briefText,
  fresh,
  busy,
  onStatus,
}: {
  lead: Lead;
  briefText: string | null;
  fresh: boolean;
  busy: boolean;
  onStatus: (lead: Lead, status: LeadReviewStatus) => void;
}) {
  const subline = lead.headline ?? (lead.source === "web" ? lead.website : null);
  return (
    <Card className={cn("space-y-3 px-4 py-4 sm:px-[18px]", fresh && "border-accent/40")}>
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 space-y-0.5">
          <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
            {fresh && <Badge tone="accent">Just found</Badge>}
            <h3 className="text-[16px] font-semibold text-ink">{lead.name || lead.handle || "Unnamed"}</h3>
            <span className="text-[13px] text-sub">{byline(lead)}</span>
          </div>
          {subline && <p className="text-[13px] text-sub">{subline}</p>}
        </div>
        {briefText && (
          <span
            title="The brief that found this person"
            className="max-w-[280px] truncate rounded-full bg-panel2 px-2.5 py-0.5 text-[12px] text-sub"
          >
            {briefText}
          </span>
        )}
      </div>

      {lead.reason && (
        <p className="text-[15px] leading-relaxed text-ink">
          <strong className="font-semibold">Why:</strong> {lead.reason}
        </p>
      )}

      {lead.evidence.length > 0 && (
        <div className="space-y-1.5">
          {lead.evidence.slice(0, 3).map((e) => (
            <div key={e.url} className="rounded-lg bg-panel2 px-3 py-2 text-[13px] leading-snug text-ink">
              &ldquo;{e.quote}&rdquo; —{" "}
              <a href={e.url} target="_blank" rel="noreferrer" className="text-accent-hi hover:underline">
                {platformLabel(lead.platform)}
                {e.at ? `, ${ago(e.at)}` : ""}
              </a>
            </div>
          ))}
        </div>
      )}

      {lead.angle && (
        <p className="text-[13px] text-sub">
          <strong className="font-semibold text-ink">Opening angle:</strong> {lead.angle}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2.5 border-t border-edge pt-3">
        <div className="flex flex-wrap items-center gap-2">
          <ContactButtons lead={lead} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(lead, "discarded")}>
            Discard
          </Button>
          <Button size="sm" disabled={busy} onClick={() => onStatus(lead, "contacted")}>
            Mark contacted
          </Button>
        </div>
      </div>
    </Card>
  );
}

export function LeadRow({
  lead,
  busy,
  onStatus,
}: {
  lead: Lead;
  busy: boolean;
  onStatus: (lead: Lead, status: LeadReviewStatus) => void;
}) {
  const what = lead.headline ?? lead.website ?? (lead.handle ? `@${lead.handle}` : null);
  const contacted = lead.status === "contacted";
  const left = daysLeft(lead.discardedAt);
  const when = contacted
    ? `contacted ${shortDate(lead.contactedAt)}`
    : `discarded ${shortDate(lead.discardedAt)}${left !== null ? ` · deleted in ${left} ${left === 1 ? "day" : "days"}` : ""}`;
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2.5 border-b border-edge px-[18px] py-3.5 last:border-b-0">
      <div className="min-w-0 flex-[1_1_280px] space-y-0.5">
        <p className="text-[15px] font-semibold text-ink">{lead.name || lead.handle || "Unnamed"}</p>
        <p className="text-[13px] text-sub">
          {[platformLabel(lead.platform), what, when].filter(Boolean).join(" · ")}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {contacted && <ContactButtons lead={lead} compact />}
        <Button
          size="sm"
          variant={contacted ? "ghost" : "outline"}
          disabled={busy}
          onClick={() => onStatus(lead, "new")}
        >
          {contacted ? "Move back to New" : "Restore to New"}
        </Button>
      </div>
    </div>
  );
}
