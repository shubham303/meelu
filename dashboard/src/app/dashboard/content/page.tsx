"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus, Sparkles } from "lucide-react";
import { useAgentTasks } from "../agent-tasks";
import * as chips from "@/features/prompt-chips/content";
import { PageEnter } from "@/components/animate";
import { Badge, Button, Card, EmptyState, IconButton, Input, PageHeader, Spinner } from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { formatRelative } from "@/lib/utils";
import type { ContentPieceSlim } from "./types";

export default function ContentPage() {
  const isApp = useIsApp();
  const router = useRouter();
  const [search, setSearch] = useState("");
  const [launchErr, setLaunchErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const path = useMemo(() => {
    const q = new URLSearchParams({ page_size: "100" });
    if (search.trim()) q.set("search", search.trim());
    return `/api/v1/content/pieces?${q}`;
  }, [search]);
  const { data, loading, error, refresh } = useApi<ContentPieceSlim[]>(path);
  const { launchTask } = useAgentTasks();

  const pieces = useMemo(() => data ?? [], [data]);

  const createBlank = async () => {
    setCreating(true);
    setLaunchErr(null);
    try {
      const created = await api<{ id: string }>("/api/v1/content/pieces", {
        method: "POST",
        body: { title: "Untitled piece" },
      });
      router.push(`/dashboard/content/${created.id}`);
    } catch (e) {
      setLaunchErr(e instanceof Error ? e.message : "Could not create the piece.");
      setCreating(false);
    }
  };

  return (
    <PageEnter>
      <PageHeader
        title="Content"
        description="Pages written for your website — title, H1, meta description, slug, target keyword and body, grounded in your site and search data. You publish them yourself."
        actions={
          <>
            <Button onClick={() => void createBlank()} disabled={creating}>
              <Plus size={14} /> New piece
            </Button>
            {isApp && (
              <IconButton
                onClick={() =>
                  launchTask({
                    title: "Write a piece",
                    endpoint: "/api/agent/content-piece",
                    emptyHint:
                      "Say what the page is about and who reads it. Meelu picks the target keyword from your search data and the internal links from your crawled pages, drafts the page here, and saves it to this desk only when you say so.",
                    draft: {},
                    suggestions: chips.newPiece,
                    onCreated: async () => {
                      await refresh();
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

      <div className="mb-4 flex justify-end">
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search pieces…"
          className="w-60"
        />
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
          <div className="grid grid-cols-[minmax(0,1fr)_180px_110px_80px] items-center gap-5 px-5 py-2.5 text-xs text-faint">
            <span>Piece</span>
            <span>Target keyword</span>
            <span>Warnings</span>
            <span className="text-right">Updated</span>
          </div>
          {pieces.map((row) => (
            <Link
              key={row.id}
              href={`/dashboard/content/${row.id}`}
              className="grid grid-cols-[minmax(0,1fr)_180px_110px_80px] items-center gap-5 border-t border-edge px-5 py-3.5 transition-colors hover:bg-panel2/60"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{row.title}</p>
                <p className="mt-0.5 truncate text-xs text-sub">
                  {row.slug ?? "no slug yet"} · {row.wordCount} words
                </p>
              </div>
              <span className="truncate text-sm text-ink">
                {row.targetKeyword ?? <span className="text-faint">—</span>}
              </span>
              {row.checks.length > 0 ? (
                <Badge tone="warn" className="w-fit">
                  {row.checks.length} to look at
                </Badge>
              ) : (
                <Badge tone="good" className="w-fit">
                  No warnings
                </Badge>
              )}
              <span className="text-right text-xs text-faint">{formatRelative(row.updatedAt)}</span>
            </Link>
          ))}
        </Card>
      )}
    </PageEnter>
  );
}
