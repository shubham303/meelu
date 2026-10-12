"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";
import { Check, Plus, X } from "lucide-react";
import { Button, Drawer, IconButton } from "@demo/components/ui";
import { activeSiteId } from "@demo/lib/current-site";
import { useApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";
import { refuseOnWeb, ScopeSummary, useScopeInfo } from "./bridge";

export type BriefLimitType = "count" | "choice" | "toggle";

export interface BriefLimit {
  key: string;
  label: string;
  type: BriefLimitType;
  value?: string | number | boolean;
  unit?: string;
  min?: number;
  max?: number;
  options?: Array<{ value: string; label: string }>;
  on?: string;
}

export interface BriefConnector {
  id: string;
  label: string;
  on?: boolean;
  available?: boolean;
}

export interface BriefResult {
  scope: string;
  lines: string[];
  limits: BriefLimit[];
  connectors: BriefConnector[];
  text: string;
}

export type CostTier = "L" | "M" | "H";

const savedKey = (scope: string) => `meelu.brief.${activeSiteId() ?? "nosite"}.${scope}`;

export interface SavedBrief {
  lines: string[];
  limits?: BriefLimit[];
  at: string;
}

export function recallBrief(scope: string): SavedBrief | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(savedKey(scope));
    return raw ? (JSON.parse(raw) as SavedBrief) : null;
  } catch {
    return null;
  }
}

export function rememberBrief(scope: string, brief: { lines: string[]; limits?: BriefLimit[] }) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      savedKey(scope),
      JSON.stringify({ ...brief, at: new Date().toISOString() }),
    );
  } catch {
  }
}

export function forgetBrief(scope: string) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(savedKey(scope));
  } catch {
  }
}

export function briefText({
  title,
  lines,
  limits = [],
  connectors = [],
}: {
  title?: string;
  lines: string[];
  limits?: BriefLimit[];
  connectors?: BriefConnector[];
}): string {
  const body = lines.filter((l) => l.trim()).map((l) => `- ${l.trim()}`);
  const said = limits
    .filter((l) => l.value !== undefined && l.value !== "" && l.value !== false)
    .map((l) => `${l.label.toLowerCase()}: ${limitLabel(l)}${l.unit ? ` ${l.unit}` : ""}`);
  const using = connectors.filter((c) => c.on !== false).map((c) => c.label);

  return [
    title ? `${title}.` : null,
    body.length ? `\nWhat to do:\n${body.join("\n")}` : null,
    said.length
      ? `\nLimits (enforced by the runner — do not exceed or argue with them): ${said.join("; ")}.`
      : null,
    using.length ? `\nYou may use: ${using.join(", ")}.` : null,
  ]
    .filter(Boolean)
    .join("\n");
}

function limitLabel(l: BriefLimit): string {
  if (l.type === "choice") {
    const hit = (l.options ?? []).find((o) => String(o.value) === String(l.value));
    return hit?.label ?? String(l.value ?? "");
  }
  if (l.type === "toggle") return l.on ?? "on";
  return String(l.value ?? "");
}

interface SiteProfileLite {
  name?: string;
  domain?: string;
  summary?: string;
}

function prefillLines(
  lines: string[] | undefined,
  saved: SavedBrief | null,
  profile: SiteProfileLite | null,
  subtitle?: string,
): string[] {
  if (lines && lines.length > 0) return lines.slice();
  if (saved?.lines?.length) return saved.lines.slice();

  const seeded: string[] = [];
  if (profile?.summary) seeded.push(profile.summary);
  else if (profile?.name) {
    seeded.push(`For ${profile.name}${profile.domain ? ` (${profile.domain})` : ""}.`);
  }
  if (subtitle && seeded.length === 0) seeded.push(subtitle);
  return seeded.length ? seeded : [""];
}

export interface PromptChip {
  label: string;
  prompt: string;
}

const CHIP_MAX = 44;

export function chipLabel(sentence: string): string {
  const said = sentence.trim().replace(/[.\s]+$/, "");
  const head = (said.split(/\s+[—–-]\s+|[,;:]/)[0] || said).trim();
  if (head.length <= CHIP_MAX) return head;
  const cut = head.slice(0, CHIP_MAX);
  const space = cut.lastIndexOf(" ");
  return `${(space > 12 ? cut.slice(0, space) : cut).trim()}…`;
}

export function toChips(lines: string[]): PromptChip[] {
  const seen = new Set<string>();
  const chips: PromptChip[] = [];
  for (const line of lines) {
    const prompt = line.trim();
    if (!prompt || seen.has(prompt)) continue;
    seen.add(prompt);
    chips.push({ label: chipLabel(prompt), prompt });
  }
  return chips;
}

export function PromptChips({
  chips,
  dropped,
  onDropped,
  fresh,
  label = "What it will be told",
  note = "Tap one to leave it out. Anything missing, say it below — it is a conversation, not a form.",
}: {
  chips: PromptChip[];
  dropped: string[];
  onDropped: (next: string[]) => void;
  fresh?: string[];
  label?: ReactNode;
  note?: ReactNode;
}) {
  if (chips.length === 0) return null;
  const toggle = (prompt: string) =>
    onDropped(
      dropped.includes(prompt) ? dropped.filter((p) => p !== prompt) : [...dropped, prompt],
    );

  return (
    <div>
      <p className="text-[11px] font-medium uppercase tracking-wide text-faint mb-2">{label}</p>
      <div className="flex flex-wrap gap-1.5">
        {chips.map((chip) => {
          const off = dropped.includes(chip.prompt);
          return (
            <button
              key={chip.prompt}
              type="button"
              title={chip.prompt}
              aria-pressed={!off}
              onClick={() => toggle(chip.prompt)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs text-left transition-colors cursor-pointer",
                off
                  ? "border-edge2 bg-transparent text-faint line-through decoration-faint/60"
                  : fresh?.includes(chip.prompt)
                    ? "border-accent bg-accent-soft text-accent"
                    : "border-edge2 bg-panel2 text-ink hover:border-accent",
              )}
            >
              {off ? <Plus size={11} className="shrink-0" /> : <Check size={11} className="shrink-0" />}
              {chip.label}
            </button>
          );
        })}
      </div>
      {note && <p className="mt-2 text-xs text-faint leading-relaxed">{note}</p>}
    </div>
  );
}

export function BriefLimits({
  limits,
  connectors,
  onLimits,
  onConnectors,
}: {
  limits: BriefLimit[];
  connectors: BriefConnector[];
  onLimits: (next: BriefLimit[]) => void;
  onConnectors: (next: BriefConnector[]) => void;
}) {
  if (limits.length === 0 && connectors.length === 0) return null;
  const setLimit = (key: string, value: BriefLimit["value"]) =>
    onLimits(limits.map((l) => (l.key === key ? { ...l, value } : l)));

  return (
    <div className="rounded-xl border border-edge bg-panel2/60 divide-y divide-edge">
      {limits.map((l) => (
        <div key={l.key} className="flex flex-wrap items-center gap-2.5 px-3.5 py-2.5">
          <span className="text-xs font-medium text-sub min-w-20">{l.label}</span>
          {l.type === "choice" ? (
            <div className="inline-flex rounded-lg border border-edge2 overflow-hidden">
              {(l.options ?? []).map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => setLimit(l.key, o.value)}
                  className={cn(
                    "px-2.5 py-1 text-xs transition-colors cursor-pointer",
                    String(l.value) === String(o.value)
                      ? "bg-accent text-white"
                      : "text-sub hover:bg-panel2",
                  )}
                >
                  {o.label}
                </button>
              ))}
            </div>
          ) : l.type === "toggle" ? (
            <label className="inline-flex items-center gap-1.5 text-xs text-ink cursor-pointer">
              <input
                type="checkbox"
                checked={l.value === true}
                onChange={(e) => setLimit(l.key, e.target.checked)}
                className="accent-accent"
              />
              {l.on ?? "on"}
            </label>
          ) : (
            <input
              type="number"
              value={l.value === undefined || l.value === false ? "" : String(l.value)}
              min={l.min}
              max={l.max}
              onChange={(e) =>
                setLimit(l.key, e.target.value === "" ? undefined : Number(e.target.value))
              }
              className="w-20 rounded-lg bg-panel border border-edge2 px-2 py-1 text-sm text-ink focus:outline-none focus:border-accent"
            />
          )}
          {l.unit && <span className="text-xs text-faint">{l.unit}</span>}
        </div>
      ))}

      {connectors.length > 0 && (
        <div className="flex flex-wrap items-center gap-2.5 px-3.5 py-2.5">
          <span className="text-xs font-medium text-sub min-w-20">Using</span>
          <span className="flex flex-wrap gap-1.5">
            {connectors.map((c) => (
              <button
                key={c.id}
                type="button"
                disabled={c.available === false}
                title={
                  c.available === false ? "Not connected — add it in Settings" : undefined
                }
                onClick={() =>
                  onConnectors(
                    connectors.map((x) => (x.id === c.id ? { ...x, on: x.on === false } : x)),
                  )
                }
                className={cn(
                  "rounded-lg border px-2.5 py-1 text-xs transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
                  c.on === false
                    ? "border-edge2 text-sub hover:border-accent"
                    : "border-accent/40 bg-accent-soft text-accent",
                )}
              >
                {c.label}
              </button>
            ))}
          </span>
          <span className="text-xs text-faint">the site profile is always read</span>
        </div>
      )}
    </div>
  );
}

export function TierBadge({ tier }: { tier?: CostTier }) {
  if (!tier) return null;
  return (
    <span className="ml-1 rounded bg-white/20 px-1 font-mono text-[10px] leading-4">{tier}</span>
  );
}

export interface BriefProps {
  open: boolean;
  onClose: () => void;
  scope: string;
  title: string;
  subtitle?: string;
  lines?: string[];
  chips?: PromptChip[];
  limits?: BriefLimit[];
  connectors?: BriefConnector[];
  tier?: CostTier;
  onRun: (brief: BriefResult) => void | Promise<void>;
  runLabel?: string;
  costNote?: ReactNode;
}

function DirectLaunch({
  scope,
  title,
  lines,
  onRun,
  onClose,
}: {
  scope: string;
  title: string;
  lines: string[];
  onRun: (brief: BriefResult) => void | Promise<void>;
  onClose: () => void;
}) {
  const fired = useRef(false);
  const go = useRef<() => void>(() => {});

  useEffect(() => {
    go.current = () => {
      if (refuseOnWeb(`Brief(${scope}).direct`)) return;
      const clean = lines.map((l) => l.trim()).filter(Boolean);
      void onRun({
        scope,
        lines: clean,
        limits: [],
        connectors: [],
        text: briefText({ title, lines: clean }),
      });
      onClose();
    };
  });

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;
    go.current();
  }, []);

  return null;
}

export function Brief(props: BriefProps): ReactElement | null {
  const isApp = useIsApp();
  const { open, onClose, scope, title, subtitle, lines, limits, connectors, onRun } = props;
  if (!isApp) return null;

  const decides = !!limits?.length || !!connectors?.length;
  if (open && !decides && lines?.some((l) => l.trim())) {
    return (
      <DirectLaunch
        key={`${scope} ${lines.join(" ")}`}
        scope={scope}
        title={title}
        lines={lines}
        onRun={onRun}
        onClose={onClose}
      />
    );
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={
        <div>
          <p className="font-display text-lg text-ink">{title}</p>
          {subtitle && <p className="text-xs text-sub mt-0.5">{subtitle}</p>}
        </div>
      }
    >
      <BriefForm key={`${scope} ${(lines ?? []).join(" ")}`} {...props} />
    </Drawer>
  );
}

function BriefForm({
  open,
  onClose,
  scope,
  title,
  subtitle,
  lines,
  chips,
  limits = [],
  connectors = [],
  tier = "M",
  onRun,
  runLabel = "Run",
  costNote,
}: BriefProps) {
  const { data: profile } = useApi<SiteProfileLite>(open ? "/api/v1/site" : null);
  const scopeInfo = useScopeInfo(open ? scope : null);

  const [dropped, setDropped] = useState<string[]>([]);
  const [restored, setRestored] = useState<string[] | null>(null);
  const [limitState, setLimitState] = useState<BriefLimit[]>(() =>
    limits.map((l) => ({ ...l })),
  );
  const [connectorState, setConnectorState] = useState<BriefConnector[]>(() =>
    connectors.map((c) => ({ ...c })),
  );
  const [saved, setSaved] = useState<SavedBrief | null>(() => recallBrief(scope));
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const resolved = useMemo(
    () => restored ?? prefillLines(lines, saved, profile ?? null, subtitle),
    [restored, lines, saved, profile, subtitle],
  );

  const shown = useMemo(() => chips ?? toChips(resolved), [chips, resolved]);
  const kept = useMemo(
    () => shown.filter((c) => !dropped.includes(c.prompt)).map((c) => c.prompt),
    [shown, dropped],
  );

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" && limits.length > 4) {
      console.warn(
        `[agent] Brief("${scope}") declares ${limits.length} limits. A widget exists only ` +
          "where the harness enforces the value — the rest are sentences.",
      );
    }
  }, [limits.length, scope]);

  const collect = useCallback(
    (): BriefResult => ({
      scope,
      lines: kept,
      limits: limitState,
      connectors: connectorState.filter((c) => c.on !== false),
      text: briefText({ title, lines: kept, limits: limitState, connectors: connectorState }),
    }),
    [scope, kept, limitState, connectorState, title],
  );

  async function run() {
    if (refuseOnWeb(`Brief(${scope}).run`)) return;
    const brief = collect();
    if (shown.length > 0 && brief.lines.length === 0) {
      setNote("Keep at least one — an empty brief is a worse prompt than no brief.");
      return;
    }
    setBusy(true);
    try {
      rememberBrief(scope, { lines: brief.lines, limits: brief.limits });
      await onRun(brief);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  const savedDiffers =
    !!saved?.lines?.length && saved.lines.join(" ") !== kept.join(" ");

  return (
    <div className="space-y-5">
      <PromptChips
        chips={shown}
        dropped={dropped}
        onDropped={setDropped}
        note="Tap one to leave it out. Hover to read the whole sentence it stands for."
      />

      <BriefLimits
        limits={limitState}
        connectors={connectorState}
        onLimits={setLimitState}
        onConnectors={setConnectorState}
      />

      <ScopeSummary scope={scopeInfo} className="block" />

      {note && <p className="text-xs text-bad">{note}</p>}

      <div className="flex flex-wrap items-center gap-2 border-t border-edge pt-4">
        <Button onClick={() => void run()} disabled={busy}>
          {runLabel}
          <TierBadge tier={tier} />
        </Button>
        <Button
          variant="ghost"
          onClick={() => {
            const brief = collect();
            rememberBrief(scope, { lines: brief.lines, limits: brief.limits });
            setSaved({ lines: brief.lines, limits: brief.limits, at: new Date().toISOString() });
            setNote("Saved — this brief opens here next time.");
          }}
        >
          Save as a starting point
        </Button>
        {costNote && <span className="text-xs text-faint ml-auto">{costNote}</span>}
      </div>

      {savedDiffers && saved && (
        <button
          type="button"
          onClick={() => {
            setRestored(saved.lines.slice());
            setDropped([]);
          }}
          className="text-xs text-accent underline cursor-pointer"
        >
          Restore the starting point you saved
        </button>
      )}
    </div>
  );
}

export function BriefButton({
  label,
  tier,
  onClick,
  className,
}: {
  label: string;
  tier?: CostTier;
  onClick: () => void;
  className?: string;
}) {
  const isApp = useIsApp();
  if (!isApp) return null;
  return (
    <Button size="sm" onClick={onClick} className={className}>
      {label}
      <TierBadge tier={tier} />
    </Button>
  );
}

export function BriefClose({ onClose }: { onClose: () => void }) {
  return (
    <IconButton onClick={onClose} aria-label="Close">
      <X size={15} />
    </IconButton>
  );
}
