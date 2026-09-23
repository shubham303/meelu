"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import { Button, Card, Input } from "@/components/ui";
import { cn } from "@/lib/utils";
import { api } from "@/lib/use-api";
import type {
  SocialListeningConfig,
  SocialListeningQuery,
  SocialListeningTarget,
} from "@/lib/types";
import type { PlatformInfo } from "./lib";

const SOURCE_LABEL: Record<string, string> = {
  profile: "✦ from site profile",
  suggested: "✦ suggested",
  user: "added by you",
};

const AGE_OPTIONS: Array<{ days: number; label: string }> = [
  { days: 365, label: "1 year" },
  { days: 180, label: "6 months" },
  { days: 90, label: "90 days" },
];

export function SetupTab({
  config,
  queries,
  targets,
  platformInfo,
  refreshConfig,
  refreshQueries,
  refreshTargets,
}: {
  config: SocialListeningConfig | null;
  queries: SocialListeningQuery[];
  targets: SocialListeningTarget[];
  platformInfo: PlatformInfo[];
  refreshConfig: () => Promise<void>;
  refreshQueries: () => Promise<void>;
  refreshTargets: () => Promise<void>;
}) {
  const [newQuery, setNewQuery] = useState("");
  const [newCompetitor, setNewCompetitor] = useState("");
  const [addingCompetitor, setAddingCompetitor] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const putConfig = async (patch: Partial<SocialListeningConfig>) => {
    setError(null);
    try {
      await api("/api/v1/social-listening/config", { method: "PUT", body: patch });
      await refreshConfig();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The setting did not save.");
    }
  };

  const addQuery = async () => {
    const text = newQuery.trim();
    if (!text) return;
    setNewQuery("");
    await api("/api/v1/social-listening/queries", {
      method: "POST",
      body: [{ text, enabled: true, source: "user" }],
    });
    await refreshQueries();
  };

  const toggleQuery = async (q: SocialListeningQuery) => {
    await api(`/api/v1/social-listening/queries/${q.id}`, {
      method: "PATCH",
      body: { enabled: !q.enabled },
    });
    await refreshQueries();
  };

  const removeQuery = async (q: SocialListeningQuery) => {
    await api(`/api/v1/social-listening/queries/${q.id}`, { method: "DELETE" });
    await refreshQueries();
  };

  const addCompetitor = async () => {
    const name = newCompetitor.trim();
    if (!name) return;
    setNewCompetitor("");
    setAddingCompetitor(false);
    await api("/api/v1/social-listening/targets", {
      method: "POST",
      body: [{ kind: "competitor", name, enabled: true, source: "user" }],
    });
    await refreshTargets();
  };

  const toggleTarget = async (t: SocialListeningTarget) => {
    await api(`/api/v1/social-listening/targets/${t.id}`, {
      method: "PATCH",
      body: { enabled: !t.enabled },
    });
    await refreshTargets();
  };

  const removeTarget = async (t: SocialListeningTarget) => {
    await api(`/api/v1/social-listening/targets/${t.id}`, { method: "DELETE" });
    await refreshTargets();
  };

  const togglePlatform = async (id: string, available: boolean) => {
    if (!config || !available) return;
    const has = config.platforms.includes(id);
    await putConfig({
      platforms: has ? config.platforms.filter((p) => p !== id) : [...config.platforms, id],
    });
  };

  const brands = targets.filter((t) => t.kind === "brand");
  const competitors = targets.filter((t) => t.kind === "competitor");
  const free = platformInfo.filter((p) => p.access === "direct");
  const apify = platformInfo.filter((p) => p.access === "apify");
  const apifyConnected = apify.some((p) => p.available);

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-bad">{error}</p>}

      <Card>
        <p className="text-xs font-medium text-sub mb-1">What should Meelu listen for?</p>
        <p className="text-xs text-faint mb-3">
          One conversation per line, written the way the post would read. Each run turns a query
          into search terms, then keeps only posts whose meaning is close to it.
        </p>
        <div className="space-y-2">
          {queries.map((q) => (
            <QueryRow
              key={q.id}
              query={q}
              onToggle={() => void toggleQuery(q)}
              onRemove={() => void removeQuery(q)}
            />
          ))}
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-edge2 px-3 py-2">
            <Plus size={13} className="shrink-0 text-faint" />
            <input
              value={newQuery}
              onChange={(e) => setNewQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void addQuery()}
              onBlur={() => void addQuery()}
              placeholder="people asking which tool tracks their rankings"
              className="w-full bg-transparent text-[13px] text-ink placeholder:text-faint focus:outline-none"
            />
          </div>
        </div>
        {queries.length === 0 && (
          <p className="text-xs text-faint mt-2.5">
            No queries yet — add one above, or ask Meelu to set up listening from the site profile.
          </p>
        )}
      </Card>

      <Card>
        <div className="flex items-baseline justify-between gap-3 flex-wrap mb-2">
          <p className="text-xs font-medium text-sub">Brand &amp; competitors to watch</p>
          <Button size="sm" variant="ghost" onClick={() => setAddingCompetitor((v) => !v)}>
            <Plus size={13} /> Add competitor
          </Button>
        </div>
        <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">Your brand</p>
        <div className="flex flex-wrap gap-2">
          {brands.length === 0 && (
            <p className="text-[13px] text-sub">
              No brand names yet — ask Meelu to set up listening and it fills them in.
            </p>
          )}
          {brands.map((t) => (
            <Chip
              key={t.id}
              on={t.enabled}
              label={t.name}
              onToggle={() => void toggleTarget(t)}
              onRemove={() => void removeTarget(t)}
            />
          ))}
        </div>
        <p className="text-xs font-medium uppercase tracking-wide text-faint mt-4 mb-2">
          Competitors
        </p>
        <div className="flex flex-wrap gap-2">
          {competitors.map((t) => (
            <Chip
              key={t.id}
              on={t.enabled}
              label={t.name}
              meta={SOURCE_LABEL[t.source]}
              onToggle={() => void toggleTarget(t)}
              onRemove={() => void removeTarget(t)}
            />
          ))}
          {addingCompetitor && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-dashed border-edge2 pl-3 pr-1.5 py-1 text-[13px]">
              <input
                autoFocus
                value={newCompetitor}
                onChange={(e) => setNewCompetitor(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && void addCompetitor()}
                onBlur={() => void addCompetitor()}
                placeholder="Competitor name"
                className="w-32 bg-transparent text-ink placeholder:text-faint focus:outline-none"
              />
            </span>
          )}
        </div>
        <p className="text-xs text-faint mt-2.5">
          Competitor mentions surface in the Competitor mentions tab as switch opportunities and
          market signal.
        </p>
      </Card>

      <Card>
        <p className="text-xs font-medium text-sub mb-1">Platforms</p>
        {platformInfo.length === 0 ? (
          <p className="text-[13px] text-sub">
            Platform availability is checked on your device, so picking platforms works in the Meelu
            app.
          </p>
        ) : (
          <>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mt-2 mb-2">
              Free — no setup
            </p>
            <div className="flex flex-wrap gap-2">
              {free.map((p) => (
                <PlatformChip
                  key={p.id}
                  info={p}
                  on={!!config?.platforms.includes(p.id)}
                  onToggle={() => void togglePlatform(p.id, p.available)}
                />
              ))}
            </div>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mt-4 mb-2">
              Paid platforms (credits)
            </p>
            <div className="flex flex-wrap gap-2">
              {apify.map((p) => (
                <PlatformChip
                  key={p.id}
                  info={p}
                  on={!!config?.platforms.includes(p.id) && p.available}
                  onToggle={() => void togglePlatform(p.id, p.available)}
                />
              ))}
            </div>
            {!apifyConnected && (
              <p className="text-xs text-sub mt-2.5">
                These platforms are not enabled on the server yet.
              </p>
            )}
          </>
        )}
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <p className="text-xs font-medium text-sub mb-3">
            Noise filters — applied before any LLM sees a post
          </p>
          <div className="space-y-2.5 text-[13px] text-ink">
            <label className="flex items-center gap-2">
              Drop posts older than
              <select
                className="rounded-lg border border-edge2 bg-panel2 px-2 py-1 text-[13px] cursor-pointer focus:outline-none focus:border-accent"
                value={config?.maxAgeDays ?? 365}
                onChange={(e) => void putConfig({ maxAgeDays: Number(e.target.value) })}
              >
                {AGE_OPTIONS.map((o) => (
                  <option key={o.days} value={o.days}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config?.dropDeadPosts ?? true}
                onChange={(e) => void putConfig({ dropDeadPosts: e.target.checked })}
              />
              Drop archived, locked and 404 posts
            </label>
            <NumberSetting
              label="Min similarity to a query"
              step={0.05}
              value={config?.minSimilarity ?? 0.8}
              onSave={(v) => void putConfig({ minSimilarity: Math.min(1, Math.max(0, v)) })}
            />
          </div>
        </Card>
        <Card>
          <p className="text-xs font-medium text-sub mb-3">Run</p>
          <div className="space-y-3 text-[13px] text-ink">
            <div className="flex items-center justify-between gap-3">
              Schedule
              <span className="inline-flex gap-0.5 rounded-lg border border-edge2 bg-panel2 p-[3px]">
                {([null, "daily", "weekly"] as const).map((s) => (
                  <button
                    key={s ?? "off"}
                    onClick={() => void putConfig({ schedule: s })}
                    className={cn(
                      "cursor-pointer rounded-md px-3 py-1 text-[13px] transition-colors capitalize",
                      (config?.schedule ?? null) === s
                        ? "bg-panel font-medium text-ink shadow-[0_1px_2px_#1f2d3d14]"
                        : "text-sub hover:text-ink",
                    )}
                  >
                    {s ?? "Off"}
                  </button>
                ))}
              </span>
            </div>
            <NumberSetting
              label="Results per search term"
              value={config?.resultsPerKeyword ?? 50}
              onSave={(v) => void putConfig({ resultsPerKeyword: Math.max(1, Math.round(v)) })}
            />
            <NumberSetting
              label="Min relevance to keep"
              step={0.1}
              value={config?.minRelevance ?? 0.6}
              onSave={(v) => void putConfig({ minRelevance: Math.min(1, Math.max(0, v)) })}
            />
          </div>
        </Card>
      </div>
    </div>
  );
}

function QueryRow({
  query,
  onToggle,
  onRemove,
}: {
  query: SocialListeningQuery;
  onToggle: () => void;
  onRemove: () => void;
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border px-3 py-2 transition-colors",
        query.enabled ? "border-accent/40 bg-accent-soft/40" : "border-edge2 bg-panel",
      )}
    >
      <input
        type="checkbox"
        className="mt-1 cursor-pointer"
        checked={query.enabled}
        onChange={onToggle}
        aria-label={query.enabled ? "Disable query" : "Enable query"}
      />
      <div className="min-w-0 flex-1">
        <p className={cn("text-[13px]", query.enabled ? "text-ink" : "text-sub")}>{query.text}</p>
        <p className="mt-0.5 text-[11px] text-faint">
          {query.source === "suggested" ? "✦ suggested · " : ""}
          {query.keywords.length > 0
            ? `searches: ${query.keywords.join(", ")}`
            : "search terms are picked on the first run"}
        </p>
      </div>
      <button
        type="button"
        aria-label="Remove query"
        className="cursor-pointer text-faint hover:text-bad"
        onClick={onRemove}
      >
        <X size={14} />
      </button>
    </div>
  );
}

function Chip({
  on,
  label,
  meta,
  onToggle,
  onRemove,
}: {
  on: boolean;
  label: string;
  meta?: string;
  onToggle: () => void;
  onRemove: () => void;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[13px] cursor-pointer transition-colors",
        on ? "border-accent bg-accent-soft text-accent" : "border-edge2 bg-panel text-sub",
      )}
      onClick={onToggle}
    >
      {label}
      {meta && <span className={cn("text-[11px]", on ? "text-accent/70" : "text-faint")}>{meta}</span>}
      <button
        type="button"
        aria-label={`Remove ${label}`}
        className="cursor-pointer text-faint hover:text-bad leading-none"
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
      >
        ×
      </button>
    </span>
  );
}

function PlatformChip({
  info,
  on,
  onToggle,
}: {
  info: PlatformInfo;
  on: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={!info.available}
      title={info.available ? undefined : "Needs a connected token — set it up on the Connections screen."}
      className={cn(
        "rounded-full border px-3 py-1 text-[13px] transition-colors",
        !info.available
          ? "border-edge text-faint cursor-not-allowed opacity-60"
          : on
            ? "border-accent bg-accent-soft text-accent cursor-pointer"
            : "border-edge text-sub hover:text-ink cursor-pointer",
      )}
    >
      {info.label}
    </button>
  );
}

function NumberSetting({
  label,
  value,
  step,
  onSave,
}: {
  label: string;
  value: number;
  step?: number;
  onSave: (v: number) => void;
}) {
  const [draft, setDraft] = useState(String(value));
  const [lastValue, setLastValue] = useState(value);
  if (value !== lastValue) {
    setLastValue(value);
    setDraft(String(value));
  }
  const commit = () => {
    const n = Number(draft);
    if (!Number.isNaN(n) && n !== value) onSave(n);
  };
  return (
    <label className="flex items-center justify-between gap-3">
      {label}
      <Input
        type="number"
        step={step}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
        className="w-24"
      />
    </label>
  );
}
