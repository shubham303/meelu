"use client";

import Link from "next/link";
import { AlertTriangle, ArrowLeft } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Card, PageHeader, Spinner } from "@/components/ui";
import { useApi } from "@/lib/use-api";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../site/site-ask";
import { DomainList } from "../domain-list";
import { SEO_ASK, TaskCards } from "../task-cards";
import type { SiteSeoLists } from "../types";

export default function BacklinksPage() {
  const { data, loading, error, refresh } =
    useApi<SiteSeoLists>("/api/v1/site/seo");
  const reload = () => void refresh();

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
        description="Sites that link to your competitors but not to you, kept where an editor could plausibly link you for the same reason."
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
      <TaskCards
        title="Start a task"
        chips={chips.backlinks()}
        onRan={reload}
      />
      {loading && !data && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      {data && data.competitors.length === 0 && (
        <Card className="mb-4 flex items-center gap-2 border-warn/40 bg-warn/5 p-3 text-sm text-warn">
          <AlertTriangle size={16} className="shrink-0" />
          <span>
            Opportunities are found from your saved competitors.{" "}
            <Link href="/dashboard/seo/competitors" className="underline">
              Save some first
            </Link>
            .
          </span>
        </Card>
      )}
      {data && (
        <DomainList
          list="backlink_opportunities"
          title="Saved opportunities"
          items={data.backlinkOpportunities}
          placeholder="site.com"
          emptyHint="No opportunities saved yet. Ask Meelu to find them, or add one above."
          onChanged={reload}
        />
      )}
    </PageEnter>
  );
}
