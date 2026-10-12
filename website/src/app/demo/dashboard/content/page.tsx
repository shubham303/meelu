"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, SlidersHorizontal, Sparkles } from "lucide-react";
import { useAgentTasks } from "../agent-tasks";
import * as chips from "@demo/features/prompt-chips/content";
import { PageEnter } from "@demo/components/animate";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  IconButton,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  Tabs,
} from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { formatRelative } from "@demo/lib/utils";
import type { SiteChannel } from "@demo/lib/types";
import { ChannelDot } from "./channel-dot";
import {
  channelLabel,
  STATUS_LABEL,
  STATUS_TONE,
  STATUSES,
  type ContentPieceSlim,
  type PieceStatus,
} from "./types";

const TABS: Array<{ key: "all" | PieceStatus; label: string }> = [
  { key: "all", label: "All" },
  ...STATUSES,
];

export default function ContentPage() {
  const isApp = useIsApp();
  const router = useRouter();
  const [tab, setTab] = useState<"all" | PieceStatus>("all");
  const [channel, setChannel] = useState("any");
  const [search, setSearch] = useState("");
  const [launchErr, setLaunchErr] = useState<string | null>(null);
  const [newOpen, setNewOpen] = useState(false);

  const path = useMemo(() => {
    const q = new URLSearchParams({ page_size: "100" });
    if (tab !== "all") q.set("status", tab);
    if (channel !== "any") q.set("channel", channel);
    if (search.trim()) q.set("search", search.trim());
    return `/api/v1/content/pieces?${q}`;
  }, [tab, channel, search]);
  const { data, loading, error, refresh } = useApi<ContentPieceSlim[]>(path);
  const { data: counts, refresh: refreshCounts } = useApi<{ byStatus: Record<PieceStatus, number> }>(
    "/api/v1/content/pieces?counts=true",
  );
  const { data: channels } = useApi<SiteChannel[]>("/api/v1/content/channels");
  const { launchTask } = useAgentTasks();

  const pieces = useMemo(() => data ?? [], [data]);
  const enabled = useMemo(() => (channels ?? []).filter((c) => c.enabled), [channels]);


  return (
    <PageEnter>
      <PageHeader
        title="Content"
        description="Everything you write. Each piece is written for one channel — the website or a social platform. You post it yourself; Meelu keeps the text and checks it against the channel's limits."
        actions={
          <>
            <Link href="/demo/dashboard/content/channels">
              <Button variant="outline">
                <SlidersHorizontal size={14} /> Channels
              </Button>
            </Link>
            <Button onClick={() => setNewOpen(true)}>
              <Plus size={14} /> New piece
            </Button>
            {isApp && (
              <IconButton
                onClick={() =>
                  launchTask({
                    title: "Write a piece",
                    endpoint: "/api/agent/content-piece",
                    emptyHint:
                      "Say which channel it is for, what the piece is about and who reads it. Meelu drafts it here, and saves it to this desk only when you say so — then it opens in the editor.",
                    draft: {},
                    suggestions: chips.newPiece,
                    onCreated: async () => {
                      await refresh();
                      await refreshCounts();
                    },
                  })
                }
                aria-label="Write with the agent"
                title="Write with the agent"
                className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
              >
                <Sparkles size={16} />
              </IconButton>
            )}
          </>
        }
      />

      {error && <p className="mb-4 text-sm text-bad">{error}</p>}
      {launchErr && <p className="mb-4 text-sm text-bad">{launchErr}</p>}

      <div className="mb-5 grid grid-cols-2 gap-3">
        <Stat label="Drafts" value={counts?.byStatus.draft ?? 0} />
        <Stat label="Blocked by channel limits" value={counts?.byStatus.blocked ?? 0} tone="warn" />
      </div>

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <Tabs tabs={TABS} active={tab} onChange={(k) => setTab(k as "all" | PieceStatus)} />
        <div className="flex flex-wrap items-center gap-2 pb-5">
          <Select value={channel} onChange={(e) => setChannel(e.target.value)} className="w-44">
            <option value="any">Channel: any</option>
            {(channels ?? []).map((c) => (
              <option key={c.channelKey} value={c.channelKey}>
                {c.label}
              </option>
            ))}
          </Select>
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search pieces…"
            className="w-52"
          />
        </div>
      </div>

      {loading && <Spinner />}

      {!loading && pieces.length === 0 && (
        <EmptyState
          title="Nothing here"
          hint="Start a piece, or ask the agent to write one and it lands here as a draft."
        />
      )}

      {pieces.length > 0 && (
        <Card className="overflow-hidden p-0">
          <div className="grid grid-cols-[minmax(0,1fr)_150px_110px_80px] items-center gap-5 px-5 py-2.5 text-xs text-faint">
            <span>Piece</span>
            <span>Channel</span>
            <span>Status</span>
            <span className="text-right">Updated</span>
          </div>
          {pieces.map((row) => (
            <Link
              key={row.id}
              href={`/demo/dashboard/content/${row.id}`}
              className="grid grid-cols-[minmax(0,1fr)_150px_110px_80px] items-center gap-5 border-t border-edge px-5 py-3.5 transition-colors hover:bg-panel2/60"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{row.title}</p>
                <p className="mt-0.5 truncate text-xs text-sub">
                  {row.wordCount} words
                  {row.parentPieceId && " · cloned from another piece"}
                </p>
              </div>
              <span className="inline-flex items-center gap-2 text-sm text-ink">
                <ChannelDot channelKey={row.channelKey} size={16} />
                {channelLabel(row.channelKey)}
              </span>
              <Badge tone={STATUS_TONE[row.status]} className="w-fit">
                {STATUS_LABEL[row.status]}
              </Badge>
              <span className="text-right text-xs text-faint">{formatRelative(row.updatedAt)}</span>
            </Link>
          ))}
        </Card>
      )}

      {newOpen && (
        <NewPieceModal
          channels={enabled}
          onClose={() => setNewOpen(false)}
          onCreated={(id) => router.push(`/demo/dashboard/content/${id}`)}
          onError={setLaunchErr}
        />
      )}
    </PageEnter>
  );
}

function Stat({ label, value, tone }: { label: string; value: number; tone?: "warn" }) {
  return (
    <Card className="px-4 py-3">
      <p className="text-xs text-faint">{label}</p>
      <p className={`font-display text-2xl ${tone === "warn" && value > 0 ? "text-warn" : "text-ink"}`}>
        {value}
      </p>
    </Card>
  );
}

function NewPieceModal({
  channels,
  onClose,
  onCreated,
  onError,
}: {
  channels: SiteChannel[];
  onClose: () => void;
  onCreated: (id: string) => void;
  onError: (message: string | null) => void;
}) {
  const [mode, setMode] = useState<"blank" | "clone">("blank");
  const [title, setTitle] = useState("");
  const [channel, setChannel] = useState("website");
  const [source, setSource] = useState("");
  const [busy, setBusy] = useState(false);
  const { data } = useApi<ContentPieceSlim[]>("/api/v1/content/pieces?page_size=100");
  const candidates = data ?? [];

  const create = async () => {
    setBusy(true);
    onError(null);
    try {
      const body: Record<string, unknown> =
        mode === "clone"
          ? { cloneFromPieceId: source, channelKey: channel, ...(title.trim() ? { title: title.trim() } : {}) }
          : { title: title.trim() || "Untitled piece", channelKey: channel };
      const created = await api<{ id: string }>("/api/v1/content/pieces", { method: "POST", body });
      onCreated(created.id);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Could not create the piece.");
      setBusy(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="New piece">
      <div className="space-y-4">
        <div className="flex gap-2">
          <Button variant={mode === "blank" ? "primary" : "outline"} size="sm" onClick={() => setMode("blank")}>
            Start blank
          </Button>
          <Button
            variant={mode === "clone" ? "primary" : "outline"}
            size="sm"
            onClick={() => setMode("clone")}
            disabled={candidates.length === 0}
          >
            Clone an existing piece
          </Button>
        </div>

        {mode === "clone" && (
          <Select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Choose a piece to copy…</option>
            {candidates.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title} · {channelLabel(p.channelKey)}
              </option>
            ))}
          </Select>
        )}

        <Select value={channel} onChange={(e) => setChannel(e.target.value)}>
          {channels.map((c) => (
            <option key={c.channelKey} value={c.channelKey}>
              {c.label}
            </option>
          ))}
        </Select>

        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={mode === "clone" ? "Title (defaults to “… (copy)”)" : "Title"}
          autoFocus
        />

        <p className="text-xs text-faint">
          {mode === "clone"
            ? "The text is copied into a new piece for the channel you pick. The new piece remembers where it came from."
            : "A piece is written for one channel. To reuse the text somewhere else, clone it."}
        </p>

        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={() => void create()} disabled={busy || (mode === "clone" && !source)}>
            Create
          </Button>
        </div>
      </div>
    </Modal>
  );
}
