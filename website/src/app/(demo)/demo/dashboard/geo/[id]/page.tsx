"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, RotateCw, Sparkles, Trash2 } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Button, ConfirmDelete, IconButton, PageHeader, Spinner } from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import type { GeoQuery } from "@demo/lib/types";
import { useAgentTasks } from "../../agent-tasks";
import { CheckBody, PrimaryAction } from "../check-body";
import { CheckProgress } from "../check-progress";
import { isRunning } from "../lib";

const POLL_MS = 3000;

export default function GeoQuestionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const { data: query, loading, error: loadError, refresh } = useApi<GeoQuery>(`/api/v1/geo/queries/${id}`);
  const [checking, setChecking] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const running = query ? isRunning(query) : false;

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, refresh]);

  const checkNow = async () => {
    setChecking(true);
    setError(null);
    try {
      await api("/api/v1/geo/checks", { method: "POST", body: { queryIds: [id] } });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The check did not start.");
    } finally {
      setChecking(false);
    }
  };

  const stopTracking = async () => {
    await api(`/api/v1/geo/queries/${id}`, { method: "DELETE" });
    router.push("/demo/dashboard/geo");
  };

  if (loading && !query) return <Spinner />;
  if (loadError || !query) return <p className="text-sm text-bad">{loadError ?? "Not found"}</p>;

  const check = query.latestCheck;

  const ask = () =>
    launchTask({
      title: `GEO: ${query.text}`,
      endpoint: "/api/agent/ask-geo",
      emptyHint: "Ask why this question is not fully answered, or plan what the page should add.",
      draft: { question: `"${query.text}" (id ${query.id})` },
      onWrote: () => void refresh(),
    });

  return (
    <PageEnter>
      <Link href="/demo/dashboard/geo" className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink">
        <ArrowLeft size={14} /> GEO
      </Link>
      <PageHeader
        title={query.text}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            {check?.status === "done" && <PrimaryAction check={check} />}
            <Button variant="outline" onClick={() => void checkNow()} disabled={running || checking}>
              <RotateCw size={13} /> {check ? "Check again" : "Check now"}
            </Button>
            <Button variant="outline" className="hover:text-bad" onClick={() => setRemoving(true)}>
              <Trash2 size={13} /> Stop tracking
            </Button>
            {isApp && (
              <IconButton
                title="Ask Meelu about this question"
                aria-label="Ask Meelu about this question"
                className="h-9 w-9 border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
                onClick={ask}
              >
                <Sparkles size={16} />
              </IconButton>
            )}
          </div>
        }
      />

      {error && <p className="mb-4 text-sm text-bad">{error}</p>}

      <div className="max-w-3xl">
        {!check ? (
          <p className="text-sm text-sub">
            Not checked yet. A check finds your closest pages, judges whether they answer this exact question, and asks
            ChatGPT, Claude and Google&apos;s AI Overview the same thing.
          </p>
        ) : running ? (
          <CheckProgress progress={check.progress} />
        ) : check.status === "error" ? (
          <p className="text-sm text-bad">{check.error ?? "The check failed."}</p>
        ) : check.status === "stopped" ? (
          <p className="text-sm text-sub">The check was stopped before it finished.</p>
        ) : (
          <CheckBody check={check} />
        )}
      </div>

      <ConfirmDelete
        open={removing}
        onClose={() => setRemoving(false)}
        onConfirm={stopTracking}
        what="this question and its checks"
      />
    </PageEnter>
  );
}
