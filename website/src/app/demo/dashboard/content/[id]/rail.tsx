"use client";

import Link from "next/link";
import { Trash2 } from "lucide-react";
import { Badge, Button } from "@demo/components/ui";
import type { SiteChannel } from "@demo/lib/types";
import { ChannelDot } from "../channel-dot";
import { channelLabel, STATUS_LABEL, type ContentPiece } from "../types";

export function Rail({
  piece,
  channel,
  onDelete,
}: {
  piece: ContentPiece;
  channel: SiteChannel | undefined;
  onDelete: () => void;
}) {
  return (
    <aside className="flex w-[300px] shrink-0 flex-col gap-7 overflow-y-auto border-l border-edge bg-panel p-6">
      <section className="flex flex-col gap-3.5">
        <p className="text-[10px] font-medium uppercase tracking-[.08em] text-faint">Piece</p>
        <div>
          <p className="text-xs font-medium text-sub mb-1.5">Channel</p>
          <p className="inline-flex items-center gap-2 text-sm text-ink">
            <ChannelDot channelKey={piece.channelKey} size={16} />
            {channelLabel(piece.channelKey)}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-faint">
            A piece is written for one channel. To take the text somewhere else, clone it from the
            Content desk.
          </p>
        </div>
        <div>
          <p className="text-xs font-medium text-sub mb-1.5">Status</p>
          <p className="text-sm text-ink">{STATUS_LABEL[piece.status]}</p>
          {piece.checks.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {piece.checks.map((c) => (
                <Badge key={c.code} tone={c.level === "block" ? "bad" : "warn"} className="whitespace-normal">
                  {c.message}
                </Badge>
              ))}
            </div>
          )}
          <p className="mt-1 text-xs leading-relaxed text-faint">
            Meelu keeps the text and checks it against {channelLabel(piece.channelKey)}&apos;s limits. Copy it out and
            post it yourself.
          </p>
        </div>
        {channel && channel.rules.length > 0 && (
          <div>
            <p className="text-xs font-medium text-sub mb-1.5">Rules for {channel.label}</p>
            <ul className="space-y-1 text-xs leading-relaxed text-sub">
              {channel.rules.slice(0, 6).map((r) => (
                <li key={r}>· {r}</li>
              ))}
            </ul>
            <Link href="/demo/dashboard/content/channels" className="mt-1 inline-block text-xs text-accent hover:underline">
              All rules
            </Link>
          </div>
        )}
        {piece.parentPieceId && (
          <p className="text-xs leading-relaxed text-faint">
            Started from{" "}
            <Link href={`/demo/dashboard/content/${piece.parentPieceId}`} className="text-accent hover:underline">
              another piece
            </Link>
            .
          </p>
        )}
      </section>

      <div className="mt-auto">
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="text-bad hover:text-bad"
        >
          <Trash2 size={13} /> Delete piece
        </Button>
      </div>
    </aside>
  );
}
