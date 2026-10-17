"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, ArrowLeft, ExternalLink } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Badge, Button, Card, PageHeader, Spinner } from "@/components/ui";
import { api, useApi, usePagedApi } from "@/lib/use-api";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../site/site-ask";
import { SEO_ASK, TaskCards } from "../task-cards";
import type { BacklinkOpportunity, Competitor } from "../types";

const PAGE_SIZE = 25;

export default function BacklinksPage() {
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const competitors = useApi<Competitor[]>("/api/v1/site/seo/competitors");
  const found = usePagedApi<BacklinkOpportunity>(
    `/api/v1/site/seo/backlink-opportunities?page=${page}&page_size=${PAGE_SIZE}`,
  );
  const reload = () => {
    void found.refresh();
    void competitors.refresh();
  };
  const rows = found.data?.data ?? [];
  const pagination = found.data?.pagination;

  async function dismiss(domain: string) {
    setBusy(domain);
    setError(null);
    try {
      await api("/api/v1/site/seo/backlink-opportunities/dismiss", {
        method: "POST",
        body: { domains: [domain] },
      });
      void found.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  return (
    <PageEnter>
      <Link
        href="/dashboard/seo"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink"
      >
        <ArrowLeft size={14} /> SEO
      </Link>
      <PageHeader
        title="Backlink opportunities"
        description="Sites that link to your competitors but not to you. Links that look spammy, paid or too weak to help are left out."
        actions={
          <SiteAskButton
            title="Ask — Backlinks"
            hint="Ask which sites are worth asking for a link, and why."
            suggestions={chips.backlinks()}
            endpoint={SEO_ASK}
            onRan={reload}
          />
        }
      />
      <TaskCards title="Start a task" chips={chips.backlinks()} onRan={reload} />
      {competitors.data && competitors.data.length === 0 && (
        <Card className="mb-4 flex items-center gap-2 border-warn/40 bg-warn/5 p-3 text-sm text-warn">
          <AlertTriangle size={16} className="shrink-0" />
          <span>
            Opportunities come from your saved competitors&apos; backlinks.{" "}
            <Link href="/dashboard/seo/competitors" className="underline">
              Add a competitor first
            </Link>
            .
          </span>
        </Card>
      )}
      {found.loading && !found.data && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {(found.error || error) && (
        <p className="mb-3 text-sm text-bad">{found.error ?? error}</p>
      )}
      {found.data && (
        <Card className="overflow-hidden p-0">
          <div className="border-b border-edge px-4 py-4">
            <h2 className="font-display text-lg text-ink">Opportunities</h2>
            <p className="text-xs text-sub">
              {pagination?.total ?? 0} sites, the ones linking to the most
              competitors first.
            </p>
          </div>
          {rows.length === 0 ? (
            <p className="px-4 py-8 text-center text-sm text-sub">
              No opportunities yet. They appear once you fetch a competitor&apos;s backlinks on the Competitors screen.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] border-collapse text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-sub">
                    <th className="px-4 py-2.5 font-medium">Site</th>
                    <th className="px-3 py-2.5 font-medium">Links to</th>
                    <th className="px-3 py-2.5 text-right font-medium">
                      Domain rank
                    </th>
                    <th className="px-3 py-2.5 text-right font-medium">Spam</th>
                    <th className="px-3 py-2.5 font-medium">Link</th>
                    <th className="px-4 py-2.5">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((o) => (
                    <tr key={o.domain} className="border-t border-edge">
                      <td className="px-4 py-3">
                        <span className="font-medium text-ink">{o.domain}</span>
                        <a
                          href={o.exampleUrl}
                          target="_blank"
                          rel="noreferrer"
                          className="flex max-w-xs items-center gap-1 truncate text-xs text-accent hover:text-accent-hi"
                        >
                          <span className="truncate">
                            {o.exampleAnchor || o.exampleUrl}
                          </span>
                          <ExternalLink size={11} className="shrink-0" />
                        </a>
                      </td>
                      <td className="px-3 py-3">
                        <span className="flex flex-wrap gap-1">
                          {o.linksTo.map((d) => (
                            <Badge key={d}>{d}</Badge>
                          ))}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-sub">
                        {o.domainRank ?? "—"}
                      </td>
                      <td className="px-3 py-3 text-right tabular-nums text-sub">
                        {o.domainSpamScore ?? o.backlinkSpamScore ?? "—"}
                      </td>
                      <td className="px-3 py-3">
                        <Badge tone={o.dofollow ? "good" : "neutral"}>
                          {o.dofollow ? "follow" : "nofollow"}
                        </Badge>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={busy !== null}
                          onClick={() => void dismiss(o.domain)}
                        >
                          Dismiss
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between border-t border-edge px-4 py-3 text-xs text-sub">
              <span>
                Page {pagination.page} of {pagination.total_pages}
              </span>
              <span className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </span>
            </div>
          )}
        </Card>
      )}
    </PageEnter>
  );
}
