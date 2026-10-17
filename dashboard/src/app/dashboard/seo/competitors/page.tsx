"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { PageHeader, Spinner } from "@/components/ui";
import { useApi } from "@/lib/use-api";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../site/site-ask";
import { CompetitorList } from "../competitor-list";
import { SEO_ASK, TaskCards } from "../task-cards";
import type { Competitor } from "../types";

export default function CompetitorsPage() {
  const { data, loading, error, refresh } = useApi<Competitor[]>(
    "/api/v1/site/seo/competitors",
  );
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
        description="Domains chasing the same searchers for the same thing. Adding one looks up its domain rank and backlinks, which feed your backlink opportunities."
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
        <CompetitorList competitors={data} onChanged={reload} />
      )}
    </PageEnter>
  );
}
