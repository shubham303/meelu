"use client";

import { useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Button, Card, EmptyState, PageHeader, Spinner } from "@demo/components/ui";
import { usePagedApi } from "@demo/lib/use-api";
import { formatRelative } from "@demo/lib/utils";
import type { AnalyticsReportSummary } from "@demo/lib/types";

const PAGE_SIZE = 20;

export default function AnalyticsReportsPage() {
  const [page, setPage] = useState(1);
  const { data, loading, error } = usePagedApi<AnalyticsReportSummary>(
    `/api/v1/analytics/reports?page=${page}&page_size=${PAGE_SIZE}`,
  );
  const reports = data?.data ?? [];
  const pagination = data?.pagination;

  return (
    <PageEnter>
      <PageHeader
        title="Reports"
        description="Answers you kept from the Analytics chat, newest first."
      />
      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-sm text-bad">{error}</p>
      ) : reports.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports yet"
          hint="Ask a question in the Analytics chat, then press Save as report under the answer."
        />
      ) : (
        <Card className="p-0">
          <ul className="divide-y divide-edge">
            {reports.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/demo/dashboard/analytics/reports/${r.id}`}
                  className="flex items-baseline justify-between gap-4 px-5 py-3 transition-colors hover:bg-panel2"
                >
                  <span className="truncate text-sm text-ink">{r.title}</span>
                  <span className="shrink-0 text-xs text-faint">{formatRelative(r.updatedAt)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
      {pagination && pagination.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-2">
          <span className="text-xs text-faint">
            Page {pagination.page} of {pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={!pagination.has_prev}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={!pagination.has_next}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </PageEnter>
  );
}
