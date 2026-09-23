"use client";

import { useEffect, useMemo, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { Badge, Button, Card, Select, Spinner } from "@/components/ui";
import { api, useApi, usePagedApi } from "@/lib/use-api";
import type { SeoCompetitor, SeoKeyword, SeoSiteState } from "@/lib/types";

const PAGE_SIZE = 50;

const SOURCES = [
  "gsc",
  "ranked",
  "ideas",
  "competitor",
  "serp_paa",
  "serp_related",
  "user",
];

export function Keywords({
  state,
  onChanged,
}: {
  state: SeoSiteState | null;
  onChanged: () => void;
}) {
  const [q, setQ] = useState("");
  const [needle, setNeedle] = useState("");
  const [source, setSource] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => {
      setNeedle(q.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
    });
    if (needle) params.set("search", needle);
    if (source) params.set("source", source);
    return `/api/v1/seo/keywords?${params}`;
  }, [page, needle, source]);

  const { data: paged, loading, error } = usePagedApi<SeoKeyword>(path);
  const rows = paged?.data ?? null;
  const pagination = paged?.pagination ?? null;

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Brand state={state} onChanged={onChanged} />
        <Competitors onChanged={onChanged} />
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <SearchIcon
            size={13}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint"
          />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter keywords"
            className="w-full rounded-lg border border-edge2 bg-panel2 py-1.5 pl-8 pr-3 text-xs text-ink placeholder:text-faint focus:border-accent focus:outline-none"
          />
        </div>
        <Select
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
          className="w-auto text-xs"
        >
          <option value="">Any source</option>
          {SOURCES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </Select>
      </div>

      {error && <p className="text-sm text-bad">{error}</p>}
      {loading && rows === null && !error && (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      )}
      {rows !== null && rows.length === 0 && (
        <p className="text-sm text-sub">
          No keywords yet. They arrive from Search Console when it syncs, and
          from the vendor when the agent collects.
        </p>
      )}
      {rows !== null && rows.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-edge bg-panel">
          <table className="w-full text-xs">
            <thead className="text-left text-faint">
              <tr className="border-b border-edge">
                <th className="px-3 py-2 font-normal">Keyword</th>
                <th className="px-3 py-2 font-normal">Source</th>
                <th className="px-3 py-2 text-right font-normal">Volume</th>
                <th className="px-3 py-2 text-right font-normal">KD</th>
                <th className="px-3 py-2 font-normal">Intent</th>
                <th className="px-3 py-2 text-right font-normal">Impr. 28d</th>
                <th className="px-3 py-2 text-right font-normal">Clicks 28d</th>
                <th className="px-3 py-2 text-right font-normal">Our pos.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((k) => (
                <tr key={k.id} className="border-b border-edge last:border-b-0">
                  <td className="px-3 py-2 text-ink">
                    {k.keyword}{" "}
                    {k.branded && <Badge tone="neutral">brand</Badge>}
                  </td>
                  <td className="px-3 py-2 text-sub">{k.firstSource}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-sub">
                    {k.volume ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-sub">
                    {k.difficulty ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-sub">{k.intent ?? "—"}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-sub">
                    {k.impressions28D}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-sub">
                    {k.clicks28D}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums text-sub">
                    {k.ourPosition ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {pagination && pagination.total_pages > 1 && (
        <div className="mt-3 flex items-center justify-between text-xs text-sub">
          <span>
            Page {pagination.page} of {pagination.total_pages} ·{" "}
            {pagination.total} keywords
          </span>
          <div className="flex gap-1.5">
            <Button
              size="sm"
              variant="outline"
              disabled={!pagination.has_prev}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={!pagination.has_next}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Brand({
  state,
  onChanged,
}: {
  state: SeoSiteState | null;
  onChanged: () => void;
}) {
  const saved = (state?.brandTerms ?? []).join(", ");
  const [draft, setDraft] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const terms = draft ?? saved;
  const setTerms = setDraft;

  const save = async () => {
    setBusy(true);
    try {
      await api("/api/v1/seo/state", {
        method: "PATCH",
        body: {
          brandTerms: terms
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        },
      });
      setDraft(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const rollup = async () => {
    setBusy(true);
    try {
      await api("/api/v1/seo/rollup", { method: "POST" });
      await api("/api/v1/seo/precompute", { method: "POST" });
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-sm font-medium text-ink">Brand terms</h3>
        <p className="text-xs text-sub">
          Queries containing these are branded and left out of every strategy.
        </p>
      </div>
      <input
        value={terms}
        onChange={(e) => setTerms(e.target.value)}
        placeholder="acme, acme coffee"
        className="w-full rounded-lg border border-edge2 bg-panel2 px-3 py-1.5 text-xs text-ink placeholder:text-faint focus:border-accent focus:outline-none"
      />
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" disabled={busy} onClick={save}>
          Save
        </Button>
        <Button size="sm" variant="ghost" disabled={busy} onClick={rollup}>
          Rebuild from Search Console
        </Button>
        {state?.rollupAt && (
          <span className="text-xs text-faint">
            rolled up {new Date(state.rollupAt).toLocaleString()}
          </span>
        )}
      </div>
    </Card>
  );
}

function Competitors({ onChanged }: { onChanged: () => void }) {
  const { data, refresh } = useApi<SeoCompetitor[]>("/api/v1/seo/competitors");
  const [busy, setBusy] = useState<string | null>(null);
  const rows = data ?? [];

  const set = async (id: string, state: "confirmed" | "ignored") => {
    setBusy(id);
    try {
      await api(`/api/v1/seo/competitors/${id}`, {
        method: "PATCH",
        body: { state },
      });
      await refresh();
      onChanged();
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-sm font-medium text-ink">Competitors</h3>
        <p className="text-xs text-sub">
          Only confirmed domains feed the gap strategy.
        </p>
      </div>
      {rows.length === 0 && (
        <p className="text-xs text-faint">
          None found yet. Run “Analyse competitors”.
        </p>
      )}
      <ul className="space-y-1.5">
        {rows.map((c) => (
          <li
            key={c.id}
            className="flex items-center justify-between gap-2 text-xs"
          >
            <span className="min-w-0 truncate text-ink">
              {c.domain}
              {c.intersections !== null && c.intersections !== undefined && (
                <span className="ml-1 text-faint">
                  · {c.intersections} shared
                </span>
              )}
            </span>
            <span className="flex shrink-0 items-center gap-1">
              {c.state === "confirmed" && <Badge tone="good">confirmed</Badge>}
              {c.state === "ignored" && <Badge tone="neutral">ignored</Badge>}
              {c.state !== "confirmed" && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy === c.id}
                  onClick={() => set(c.id, "confirmed")}
                >
                  Confirm
                </Button>
              )}
              {c.state !== "ignored" && (
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={busy === c.id}
                  onClick={() => set(c.id, "ignored")}
                >
                  Ignore
                </Button>
              )}
            </span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
