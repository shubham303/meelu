"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowRight, Cable, Check, ExternalLink, Send, X } from "lucide-react";
import { Badge, Button, Field, Input, Select } from "@/components/ui";
import { api } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import {
  APP_ONLY_NOTE,
  CONNECT_NOTE,
  providerCall,
  useProviderConnected,
  type SocialProfilesResult,
} from "@/lib/providers";
import { cn } from "@/lib/utils";
import type { SiteChannel } from "@/lib/types";
import { cellInstant, dateTimeLabel, hourLabel, zonedParts } from "../calendar/time";
import { channelLabel, STATUS_LABEL, STATUS_TONE, type ContentPiece } from "../types";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export function PublishPanel({
  piece,
  channel,
  flush,
  onChanged,
  onClose,
}: {
  piece: ContentPiece;
  channel: SiteChannel | undefined;
  flush: () => Promise<boolean>;
  onChanged: () => Promise<void> | void;
  onClose: () => void;
}) {
  return (
    <aside className="flex w-[360px] shrink-0 flex-col overflow-y-auto border-l border-edge bg-panel">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-edge px-5">
        <p className="text-[10px] font-medium uppercase tracking-[.08em] text-faint">Publish</p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="inline-flex h-7 w-7 items-center justify-center rounded-md text-sub transition-colors hover:bg-panel2 hover:text-ink cursor-pointer"
        >
          <X size={14} />
        </button>
      </div>
      <div className="p-5">
        <PublishForm key={`${piece.id}:${piece.updatedAt}`} piece={piece} channel={channel} flush={flush} onChanged={onChanged} />
      </div>
    </aside>
  );
}

function PublishForm({
  piece,
  channel,
  flush,
  onChanged,
}: {
  piece: ContentPiece;
  channel: SiteChannel | undefined;
  flush: () => Promise<boolean>;
  onChanged: () => Promise<void> | void;
}) {
  const isApp = useIsApp();
  const timezone = channel?.timezone ?? "UTC";
  const slot = piece.scheduledAt ? zonedParts(new Date(piece.scheduledAt), timezone) : null;

  const [date, setDate] = useState(
    slot
      ? `${slot.year}-${String(slot.month).padStart(2, "0")}-${String(slot.day).padStart(2, "0")}`
      : "",
  );
  const [hour, setHour] = useState(slot?.hour ?? 9);
  const [postedUrl, setPostedUrl] = useState(piece.postedUrl ?? "");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [social, setSocial] = useState<SocialProfilesResult | null>(null);
  const [confirming, setConfirming] = useState(false);
  const managed = useProviderConnected("social");

  useEffect(() => {
    if (!isApp || !managed) return;
    const loadSocial = () =>
      providerCall<SocialProfilesResult>("social_profiles")
        .then(setSocial)
        .catch(() => setSocial(null));
    void loadSocial();
    const onFocus = () => void loadSocial();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [isApp, managed]);

  useEffect(() => {
    if (!isApp || !managed || piece.status !== "scheduled") return;
    void providerCall<{ reconciled: number }>("social_reconcile", { pieceIds: [piece.id] })
      .then((r) => (r.reconciled > 0 ? onChanged() : undefined))
      .catch(() => {});
  }, [isApp, managed, piece.id, piece.status, onChanged]);

  const connected =
    social?.profiles.some((p) => p.platform === piece.channelKey && p.status === "active") ?? false;

  async function connect() {
    setErr(null);
    try {
      const link = await providerCall<{ url: string }>("social_connect_link", {
        platform: piece.channelKey,
      });
      window.open(link.url, "_blank", "noopener");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not start the connection.");
    }
  }

  const isWebsite = piece.channelKey === "website";
  const terminal = piece.status === "posted";
  const queued = piece.status === "scheduled";
  const locked = terminal || queued;
  const scheduledAt = date ? slotOf(date, hour, timezone) : null;
  const slotDirty = scheduledAt !== piece.scheduledAt;
  const blocks = piece.checks.filter((c) => c.level === "block");
  const warns = piece.checks.filter((c) => c.level === "warn");
  const slotLabel = piece.scheduledAt
    ? `${dateTimeLabel(piece.scheduledAt, timezone)} (${timezone})`
    : "no slot yet";

  async function run(fn: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setErr(null);
    try {
      await flush();
      await fn();
      await onChanged();
    } catch (e) {
      setErr(e instanceof Error ? e.message : fallback);
    } finally {
      setBusy(false);
    }
  }

  const patch = (body: Record<string, unknown>) =>
    api(`/api/v1/content/pieces/${piece.id}`, { method: "PATCH", body });

  const publish = () =>
    run(
      async () => {
        if (slotDirty) await patch({ scheduledAt });
        await providerCall("social_schedule_post", {
          pieceId: piece.id,
          body: piece.bodyMarkdown,
          profiles: [piece.channelKey],
          scheduledAt: scheduledAt ?? undefined,
        });
      },
      "Could not hand this to the publisher",
    ).then(() => setConfirming(false));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={STATUS_TONE[piece.status]}>{STATUS_LABEL[piece.status]}</Badge>
        <span className="text-xs text-sub">{channelLabel(piece.channelKey)}</span>
        <span className="text-xs text-faint">{slotLabel}</span>
      </div>

      {(blocks.length > 0 || warns.length > 0) && (
        <div className="flex flex-wrap gap-1.5">
          {blocks.map((c) => (
            <Badge key={c.code} tone="bad" className="whitespace-normal">
              {c.message}
            </Badge>
          ))}
          {warns.map((c) => (
            <Badge key={c.code} tone="warn" className="whitespace-normal">
              {c.message}
            </Badge>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        <Field label="Date" hint="Leave empty to post right away.">
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} disabled={locked} />
        </Field>
        <Field label="Hour" hint={timezone}>
          <Select
            value={hour}
            onChange={(e) => setHour(Number(e.target.value))}
            disabled={locked || !date}
          >
            {HOURS.map((h) => (
              <option key={h} value={h}>
                {hourLabel(h)}
              </option>
            ))}
          </Select>
        </Field>
      </div>

      {!locked && slotDirty && (isWebsite || !isApp) && (
        <Button
          size="sm"
          disabled={busy}
          onClick={() => void run(() => patch({ scheduledAt }), "Could not save")}
        >
          Save slot
        </Button>
      )}

      {err && <p className="text-sm text-bad">{err}</p>}

      {piece.failure && !queued && (
        <div className="rounded-lg border border-bad/30 bg-bad/10 p-3 flex items-start gap-2.5">
          <AlertCircle size={14} className="text-bad shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-ink">This didn&apos;t go out.</p>
            <p className="text-xs text-sub mt-0.5">{piece.failure}</p>
          </div>
        </div>
      )}

      <div className="border-t border-edge pt-5">
        <p className="text-xs text-sub uppercase tracking-wide mb-3">Status</p>

        {queued ? (
          <div className="space-y-3">
            <p className="text-sm text-ink">
              Scheduled to go out {dateTimeLabel(piece.scheduledAt ?? "", timezone)}.
            </p>
            <p className="text-xs text-sub">
              The publisher is holding this post and will send it on its own — it marks itself
              posted once it&apos;s live. Drag it on the calendar to move it. To change the text,
              cancel the schedule first.
            </p>
            <Button
              variant="outline"
              size="sm"
              disabled={busy}
              onClick={() =>
                void run(
                  () => providerCall("social_cancel_schedule", { pieceId: piece.id }),
                  "Could not cancel that schedule",
                )
              }
            >
              Cancel schedule
            </Button>
          </div>
        ) : terminal ? (
          <div className="space-y-1.5">
            <p className="text-sm text-ink">
              {isWebsite ? "Live" : "Posted"}
              {piece.postedAt ? ` ${dateTimeLabel(piece.postedAt, timezone)}` : ""}.
            </p>
            {piece.postedUrl && (
              <a
                href={piece.postedUrl}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-accent hover:underline inline-flex items-center gap-1"
              >
                <ExternalLink size={13} /> {isWebsite ? "View the page" : "View the live post"}
              </a>
            )}
            <p className="text-xs text-faint">A posted piece is final — clone it to reuse the text.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {isApp && !isWebsite && piece.status !== "blocked" && (
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  size="sm"
                  disabled={busy || blocks.length > 0 || (managed && !connected)}
                  title={blocks[0]?.message}
                  onClick={() => (managed ? setConfirming(true) : setErr(NO_PUBLISHER))}
                >
                  <Send size={14} /> {scheduledAt ? "Schedule…" : "Publish now…"}
                </Button>
                {managed && !connected && (
                  <Button size="sm" variant="outline" onClick={() => void connect()}>
                    <Cable size={14} /> Connect {channelLabel(piece.channelKey)}
                  </Button>
                )}
              </div>
            )}

            {!isApp && !isWebsite && <p className="text-xs text-sub">{APP_ONLY_NOTE}</p>}

            {isApp && !isWebsite && managed && !connected && (
              <p className="text-xs text-warn">
                {channelLabel(piece.channelKey)} isn&apos;t connected for this website. Connect it
                first — nothing can be scheduled until the account is active.
              </p>
            )}

            {confirming && managed && (
              <div className="rounded-xl border border-accent/30 bg-accent-soft p-3 space-y-2.5">
                <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
                  This is what goes out
                </p>
                <p className="text-xs text-sub">
                  {channelLabel(piece.channelKey)} ·{" "}
                  {scheduledAt ? `${dateTimeLabel(scheduledAt, timezone)} (${timezone})` : "right now"}
                </p>
                <p className="max-h-48 overflow-y-auto whitespace-pre-wrap rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm leading-relaxed text-ink">
                  {piece.bodyMarkdown}
                </p>
                <p className="text-[11px] text-faint">
                  It goes to someone else’s platform, in this slot, and a missed slot is not
                  rescheduled — you write another one.
                </p>
                <div className="flex flex-wrap gap-1.5">
                  <Button size="sm" disabled={busy} onClick={() => void publish()}>
                    Yes — hand it to the publisher
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setConfirming(false)}>
                    Not yet
                  </Button>
                </div>
              </div>
            )}

            {err === NO_PUBLISHER && (
              <p className={cn("text-xs text-warn")}>
                {CONNECT_NOTE.social}{" "}
                <Link
                  href="/dashboard/connections"
                  className="text-accent hover:underline inline-flex items-center gap-0.5 align-baseline"
                >
                  Open Connections <ArrowRight size={12} />
                </Link>
              </p>
            )}

            {isWebsite && (
              <div className="rounded-lg border border-edge bg-panel2 p-3 space-y-2">
                <p className="text-xs text-sub">Published it on the site? Record it here with the URL.</p>
                <Input
                  value={postedUrl}
                  onChange={(e) => setPostedUrl(e.target.value)}
                  placeholder="https://…/the-page"
                />
                <Button
                  size="sm"
                  variant="outline"
                  disabled={busy}
                  onClick={() =>
                    void run(() => patch({ status: "posted", postedUrl: postedUrl || null }), "Could not update")
                  }
                >
                  <Check size={14} /> Mark live
                </Button>
              </div>
            )}
          </div>
        )}
      </div>

      {channel && (
        <p className="text-xs text-faint">
          Rules for {channel.label} live on the{" "}
          <Link href="/dashboard/content/channels" className="text-accent hover:underline">
            Channels
          </Link>{" "}
          screen.
        </p>
      )}
    </div>
  );
}

const NO_PUBLISHER = "no-publisher";

function slotOf(date: string, hour: number, tz: string): string {
  const [y, m, d] = date.split("-").map(Number);
  if (!y || !m || !d) return "";
  return cellInstant({ year: y, month: m, day: d }, hour, tz).toISOString();
}
