"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Button, Card, Input } from "@demo/components/ui";
import { api } from "@demo/lib/use-api";
import { formatRelative } from "@demo/lib/utils";
import type { Competitor, CompetitorsChange } from "./types";

const MAX_COMPETITORS = 50;

export function CompetitorList({
  competitors,
  onChanged,
}: {
  competitors: Competitor[];
  onChanged: () => void;
}) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toAdd = draft
    .split(/[\s,]+/)
    .map((d) => d.trim())
    .filter(Boolean);

  async function run(key: string, work: () => Promise<unknown>) {
    setBusy(key);
    setError(null);
    try {
      await work();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-4">
        <div>
          <h2 className="font-display text-lg text-ink">Saved competitors</h2>
          <p className="text-xs text-sub">
            {competitors.length} of {MAX_COMPETITORS}
          </p>
        </div>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!toAdd.length) return;
            void run("add", async () => {
              await api<CompetitorsChange>("/api/v1/site/seo/competitors", {
                method: "POST",
                body: { domains: toAdd },
              });
              setDraft("");
            });
          }}
        >
          <label className="sr-only" htmlFor="competitor-add">
            Competitor domain to add
          </label>
          <Input
            id="competitor-add"
            className="w-56"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="competitor.com"
          />
          <Button type="submit" disabled={!toAdd.length || busy !== null}>
            {busy === "add" ? "Adding…" : "Add"}
          </Button>
        </form>
      </div>
      {busy && busy.startsWith("fetch:") && (
        <p className="px-4 pt-3 text-sm text-sub">
          Fetching backlinks. This can take a minute.
        </p>
      )}
      {error && <p className="px-4 pt-3 text-sm text-bad">{error}</p>}
      {competitors.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-sub">
          No competitors saved yet. Add one above, or ask Meelu who holds your
          main keywords. Backlinks are fetched only when you ask, because each
          fetch uses credits.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-sub">
                <th className="px-4 py-2.5 font-medium">Domain</th>
                <th className="px-3 py-2.5 text-right font-medium">
                  Domain rank
                </th>
                <th className="px-3 py-2.5 text-right font-medium">
                  Backlinks
                </th>
                <th className="px-3 py-2.5 font-medium">Fetched</th>
                <th className="px-4 py-2.5">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {competitors.map((c) => (
                <tr key={c.id} className="border-t border-edge">
                  <td className="px-4 py-3 font-medium text-ink">{c.domain}</td>
                  <td className="px-3 py-3 text-right tabular-nums text-sub">
                    {c.domainRank ?? "—"}
                  </td>
                  <td className="px-3 py-3 text-right tabular-nums text-sub">
                    {c.backlinks.toLocaleString()}
                  </td>
                  <td className="px-3 py-3 text-sub">
                    {c.backlinksFetchedAt
                      ? formatRelative(c.backlinksFetchedAt)
                      : "not fetched"}
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center justify-end gap-2">
                      <a
                        href={`https://${c.domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 px-2 text-xs text-accent hover:text-accent-hi"
                      >
                        Open site <ExternalLink size={12} />
                      </a>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={busy !== null}
                        onClick={() =>
                          void run(`fetch:${c.id}`, () =>
                            api("/api/v1/site/seo/backlinks/fetch", {
                              method: "POST",
                              body: { domains: [c.domain] },
                            }),
                          )
                        }
                      >
                        {busy === `fetch:${c.id}`
                          ? "Fetching…"
                          : c.backlinksFetchedAt
                            ? "Refetch backlinks"
                            : "Fetch backlinks"}
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        disabled={busy !== null}
                        onClick={() =>
                          void run(c.id, () =>
                            api(`/api/v1/site/seo/competitors/${c.id}`, {
                              method: "DELETE",
                            }),
                          )
                        }
                      >
                        Remove
                      </Button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
