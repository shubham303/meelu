"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { FileText, Search as SearchIcon, X } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "@demo/components/ui";
import { REPORT_DESK_LABEL } from "@demo/features/reports/desks";
import { usePagedApi } from "@demo/lib/use-api";
import { cn, formatRelative } from "@demo/lib/utils";
import { REPORT_DESKS, type ReportDesk, type ReportSummary } from "@demo/lib/types";

const PAGE_SIZE = 20;

type DeskFilter = "all" | ReportDesk;

function reportsPath(page: number, desk: DeskFilter, q: string): string {
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
  if (desk !== "all") params.set("desk", desk);
  if (q) params.set("q", q);
  return `/api/v1/reports?${params}`;
}

export default function ReportsPage() {
  const [page, setPage] = useState(1);
  const [desk, setDesk] = useState<DeskFilter>("all");
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const { data, loading, error } = usePagedApi<ReportSummary>(reportsPath(page, desk, search));
  const reports = data?.data ?? [];
  const pagination = data?.pagination;

  const pickDesk = (next: DeskFilter) => {
    setDesk(next);
    setPage(1);
  };

  const runSearch = (e: FormEvent) => {
    e.preventDefault();
    setSearch(query.trim());
    setPage(1);
  };

  const clearSearch = () => {
    setQuery("");
    setSearch("");
    setPage(1);
  };

  const filtered = desk !== "all" || search !== "";

  return (
    <PageEnter>
      <PageHeader
        title="Reports"
        description="Results you asked Meelu to keep, from every desk, newest first."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-edge bg-panel p-0.5">
          {(["all", ...REPORT_DESKS] as DeskFilter[]).map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => pickDesk(d)}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs transition-colors",
                desk === d ? "bg-accent-soft text-accent font-medium" : "text-sub hover:text-ink",
              )}
            >
              {d === "all" ? "All" : REPORT_DESK_LABEL[d]}
            </button>
          ))}
        </div>

        <form onSubmit={runSearch} className="flex min-w-0 flex-1 items-center">
          <div className="relative min-w-0 flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search titles…"
              className="w-full rounded-lg border border-edge bg-panel py-1.5 pl-9 pr-8 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
            />
            {search && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={clearSearch}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-faint transition-colors hover:text-ink"
              >
                <X size={14} />
              </button>
            )}
          </div>
        </form>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-sm text-bad">{error}</p>
      ) : reports.length === 0 ? (
        <EmptyState
          icon={filtered ? SearchIcon : FileText}
          title={filtered ? "No reports match" : "No reports yet"}
          hint={
            filtered
              ? "Try another desk or a different search."
              : "Ask a question on Analytics, SEO or Technical SEO, then ask Meelu to save the answer as a report."
          }
        />
      ) : (
        <Card className="p-0">
          <ul className="divide-y divide-edge">
            {reports.map((r) => (
              <li key={r.id}>
                <Link
                  href={`/demo/dashboard/reports/${r.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-3 transition-colors hover:bg-panel2"
                >
                  <span className="truncate text-sm text-ink">{r.title}</span>
                  <span className="flex shrink-0 items-center gap-3">
                    <Badge>{REPORT_DESK_LABEL[r.desk]}</Badge>
                    <span className="text-xs text-faint">{formatRelative(r.updatedAt)}</span>
                  </span>
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
