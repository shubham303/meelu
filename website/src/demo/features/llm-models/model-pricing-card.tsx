"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Sparkles } from "lucide-react";
import { Badge, Button, Card, Input, Table, TCell, THead, TRow, type SortState } from "@demo/components/ui";
import {
  TIER_LABEL,
  contextLabel,
  defaultModel,
  listModels,
  price,
  setDefaultModel,
  type LlmModel,
} from "./models";

const COLS = ["Model", "Input / 1M", "Output / 1M", "Context", ""];
const SORTABLE = ["Input / 1M", "Output / 1M", "Context"];
const COLLAPSED_ROWS = 12;

function sorted(models: LlmModel[], sort: SortState | null): LlmModel[] {
  if (!sort) return models;
  const value = (m: LlmModel) =>
    sort.col === "Input / 1M"
      ? m.inputUsdPerMillion
      : sort.col === "Output / 1M"
        ? m.outputUsdPerMillion
        : m.contextLength;
  const dir = sort.dir === "asc" ? 1 : -1;
  return [...models].sort((a, b) => (value(a) - value(b)) * dir);
}

export function ModelPricingCard() {
  const [models, setModels] = useState<LlmModel[] | null>(null);
  const [current, setCurrent] = useState("");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortState | null>(null);
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([listModels(), defaultModel()])
      .then(([list, chosen]) => {
        setModels(list);
        setCurrent(chosen);
      })
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : "The model list is unavailable."));
  }, []);

  const rows = useMemo(() => {
    if (!models) return [];
    const q = query.trim().toLowerCase();
    const matched = q
      ? models.filter((m) => `${m.name} ${m.id}`.toLowerCase().includes(q))
      : models;
    return sorted(matched, sort);
  }, [models, query, sort]);

  const choose = async (id: string) => {
    setBusy(id);
    setErr(null);
    try {
      setCurrent(await setDefaultModel(id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not save.");
    } finally {
      setBusy(null);
    }
  };

  const toggleSort = (col: string) =>
    setSort((s) =>
      s?.col !== col ? { col, dir: "asc" } : s.dir === "asc" ? { col, dir: "desc" } : null,
    );

  const visible = showAll || query ? rows : rows.slice(0, COLLAPSED_ROWS);

  return (
    <Card className="mb-6">
      <div className="flex items-center gap-2.5">
        <Sparkles size={15} className="text-accent shrink-0" />
        <p className="font-medium text-ink">Default model</p>
      </div>
      <p className="text-sm text-sub mt-1">
        Tasks run on this model unless you pick another when you start one, or you saved your
        own Anthropic key above. You pay what the model costs, from your credits, with no markup.
        Prices are per million tokens.
      </p>
      {err && <p className="text-sm text-bad mt-2">{err}</p>}
      {models && (
        <>
          <Input
            className="mt-4"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${models.length} models`}
            aria-label="Search models"
          />
          <Table className="mt-3">
            <THead cols={COLS} sortable={SORTABLE} sort={sort} onSort={toggleSort} />
            <tbody>
              {visible.map((m) => (
                <TRow key={m.id}>
                  <TCell>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{m.name}</span>
                      {m.tier === "featured" && <Badge tone="accent">{TIER_LABEL.featured}</Badge>}
                    </div>
                    <span className="text-xs text-faint">{m.id}</span>
                  </TCell>
                  <TCell className="tabular-nums whitespace-nowrap">{price(m.inputUsdPerMillion)}</TCell>
                  <TCell className="tabular-nums whitespace-nowrap">{price(m.outputUsdPerMillion)}</TCell>
                  <TCell className="tabular-nums whitespace-nowrap">{contextLabel(m.contextLength)}</TCell>
                  <TCell className="text-right whitespace-nowrap">
                    {m.id === current ? (
                      <span className="inline-flex items-center gap-1 text-sm text-good">
                        <Check size={14} /> Default
                      </span>
                    ) : (
                      <Button variant="outline" onClick={() => void choose(m.id)} disabled={busy !== null}>
                        {busy === m.id ? "Saving…" : "Use"}
                      </Button>
                    )}
                  </TCell>
                </TRow>
              ))}
            </tbody>
          </Table>
          {!query && rows.length > COLLAPSED_ROWS && (
            <Button variant="ghost" className="mt-2" onClick={() => setShowAll((v) => !v)}>
              {showAll ? "Show fewer" : `Show all ${rows.length} models`}
            </Button>
          )}
        </>
      )}
    </Card>
  );
}
