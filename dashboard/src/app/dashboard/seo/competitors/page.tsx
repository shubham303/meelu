"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { PageHeader, Spinner } from "@/components/ui";
import { useApi } from "@/lib/use-api";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../site/site-ask";
import { DomainList } from "../domain-list";
import { SEO_ASK, TaskCards } from "../task-cards";
import type { SiteSeoLists } from "../types";

export default function CompetitorsPage() {
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
        title="Competitors"
        description="Domains chasing the same searchers for the same thing. Backlink opportunities are found from this list."
        actions={
          <SiteAskButton
            title="Ask — Competitors"
            hint="Ask who you compete with, or how you compare with one of them."
            suggestions={chips.competitors()}
            endpoint={SEO_ASK}
            onRan={reload}
          />
        }
      />
      <TaskCards
        title="Start a task"
        chips={chips.competitors()}
        onRan={reload}
      />
      {loading && !data && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      {data && (
        <DomainList
          list="competitors"
          title="Saved competitors"
          items={data.competitors}
          placeholder="competitor.com"
          emptyHint="No competitors saved yet. Ask Meelu to find them, or add one above."
          onChanged={reload}
        />
      )}
    </PageEnter>
  );
}
