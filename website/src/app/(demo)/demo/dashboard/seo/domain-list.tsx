"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Button, Card, Input } from "@demo/components/ui";
import { api } from "@demo/lib/use-api";
import type { SeoListChange, SeoListName } from "./types";

const MAX_ITEMS = 500;

export function DomainList({
  list,
  title,
  items,
  emptyHint,
  placeholder,
  onChanged,
}: {
  list: SeoListName;
  title: string;
  items: string[];
  emptyHint: string;
  placeholder: string;
  onChanged: () => void;
}) {
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function change(
    verb: "add" | "remove",
    domains: string[],
    key: string,
  ) {
    setBusy(key);
    setError(null);
    try {
      await api<SeoListChange>(`/api/v1/site/seo/${list}/${verb}`, {
        method: "POST",
        body: { items: domains },
      });
      if (verb === "add") setDraft("");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  const toAdd = draft
    .split(/[\s,]+/)
    .map((d) => d.trim())
    .filter(Boolean);

  return (
    <Card className="overflow-hidden p-0">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-4">
        <div>
          <h2 className="font-display text-lg text-ink">{title}</h2>
          <p className="text-xs text-sub">
            {items.length} of {MAX_ITEMS}
          </p>
        </div>
        <form
          className="flex flex-wrap gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (toAdd.length) void change("add", toAdd, "add");
          }}
        >
          <label className="sr-only" htmlFor={`${list}-add`}>
            Domain to add
          </label>
          <Input
            id={`${list}-add`}
            className="w-56"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={placeholder}
          />
          <Button type="submit" disabled={!toAdd.length || busy === "add"}>
            Add
          </Button>
        </form>
      </div>
      {error && <p className="px-4 pt-3 text-sm text-bad">{error}</p>}
      {items.length === 0 ? (
        <p className="px-4 py-8 text-center text-sm text-sub">{emptyHint}</p>
      ) : (
        <ul>
          {items.map((domain) => (
            <li
              key={domain}
              className="flex items-center justify-between gap-3 border-t border-edge px-4 py-3 first:border-t-0"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-panel2 text-sm font-semibold text-sub">
                  {domain.charAt(0).toUpperCase()}
                </span>
                <span className="truncate text-sm font-medium text-ink">
                  {domain}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <a
                  href={`https://${domain}`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-2 text-xs text-accent hover:text-accent-hi"
                >
                  Open site <ExternalLink size={12} />
                </a>
                <Button
                  variant="danger"
                  size="sm"
                  disabled={busy === domain}
                  onClick={() => void change("remove", [domain], domain)}
                >
                  Remove
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
