"use client";

import { useState } from "react";
import { Plus, Users } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Input,
  Select,
  Spinner,
  Table,
  TCell,
  THead,
  TRow,
} from "@/components/ui";
import { cn } from "@/lib/utils";
import { api, usePagedApi } from "@/lib/use-api";
import { siteHeader } from "@/lib/current-site";
import type { Lead, LeadCampaign, LeadStage, LeadSummary } from "@/lib/types";
import { leadsQuery, sourceLabel, STAGE_LABEL, STAGES, type LeadSort } from "./lib";

export function LeadsTab({
  summary,
  campaigns,
  campaignName,
  onOpen,
  version,
}: {
  summary: LeadSummary | null;
  campaigns: LeadCampaign[];
  campaignName: (id: string | null) => string | null;
  onOpen: (lead: Lead) => void;
  version: number;
}) {
  const [stage, setStage] = useState<LeadStage>("qualified");
  const [minFit, setMinFit] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [source, setSource] = useState("");
  const [sort, setSort] = useState<LeadSort>("fit");
  const [page, setPage] = useState(1);
  const [adding, setAdding] = useState(false);
  const [localVersion, setLocalVersion] = useState(0);

  const { data, loading, error } = usePagedApi<Lead>(
    leadsQuery({
      stage,
      campaignId,
      source,
      minFit,
      sort,
      page,
      page_size: 25,
      v: version + localVersion,
    }),
  );
  const leads = data?.data ?? [];
  const sourcesSeen = Array.from(new Set(leads.map((l) => l.source).filter(Boolean))) as string[];

  return (
    <div>
      <div className="grid gap-3 grid-cols-3 mb-4">
        {STAGES.map((s) => (
          <button
            key={s}
            onClick={() => {
              setStage(s);
              setPage(1);
            }}
            className={cn(
              "rounded-2xl border px-4 py-3 text-left transition-colors cursor-pointer",
              stage === s
                ? "border-accent bg-accent-soft"
                : "border-edge bg-panel hover:bg-panel2",
            )}
          >
            <span
              className={cn(
                "block text-xs font-medium",
                stage === s ? "text-accent" : "text-sub",
              )}
            >
              {STAGE_LABEL[s]}
            </span>
            <span className="block font-display text-xl text-ink mt-0.5">
              {summary?.stages[s] ?? 0}
            </span>
          </button>
        ))}
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Select
          className="w-auto"
          value={campaignId}
          onChange={(e) => {
            setCampaignId(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All campaigns</option>
          {campaigns.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
        <Select
          className="w-auto"
          value={source}
          onChange={(e) => {
            setSource(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All sources</option>
          {sourcesSeen.map((s) => (
            <option key={s} value={s}>
              {sourceLabel(s)}
            </option>
          ))}
        </Select>
        <Select
          className="w-auto"
          value={minFit}
          onChange={(e) => {
            setMinFit(e.target.value);
            setPage(1);
          }}
        >
          <option value="">Any fit</option>
          <option value="0.5">Fit ≥ 0.5</option>
          <option value="0.7">Fit ≥ 0.7</option>
          <option value="0.9">Fit ≥ 0.9</option>
        </Select>
        <div className="ml-auto inline-flex rounded-lg border border-edge2 overflow-hidden text-xs">
          {(["fit", "newest"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSort(s)}
              className={cn(
                "px-3 py-1.5 transition-colors cursor-pointer",
                sort === s ? "bg-accent-soft text-accent" : "text-sub hover:text-ink",
              )}
            >
              {s === "fit" ? "Best fit" : "Newest"}
            </button>
          ))}
        </div>
        <Button size="sm" onClick={() => setAdding((v) => !v)}>
          <Plus size={13} /> Add lead
        </Button>
      </div>

      {adding && (
        <AddLeadForm
          campaigns={campaigns}
          onClose={() => setAdding(false)}
          onAdded={() => {
            setAdding(false);
            setLocalVersion((v) => v + 1);
          }}
          onOpen={onOpen}
        />
      )}

      {loading ? (
        <Spinner />
      ) : error ? (
        <p className="text-sm text-bad">{error}</p>
      ) : leads.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No leads here"
          hint={
            stage === "qualified"
              ? "Run discovery from a campaign, or add a lead yourself — Meelu qualifies both the same way."
              : "No leads match the current filters."
          }
        />
      ) : (
        <>
          <Table>
            <THead cols={["Lead", "Campaign", "Why they fit", "Fit", "Email", ""]} />
            <tbody>
              {leads.map((lead) => (
                <TRow key={lead.id} onClick={() => onOpen(lead)}>
                  <TCell>
                    <span className="block font-medium text-ink">{lead.name}</span>
                    <span className="block text-xs text-faint">
                      {[lead.company, lead.role].filter(Boolean).join(" · ") ||
                        lead.website ||
                        sourceLabel(lead.source)}
                    </span>
                  </TCell>
                  <TCell>
                    {campaignName(lead.campaignId) ? (
                      <Badge>{campaignName(lead.campaignId)}</Badge>
                    ) : (
                      <span className="text-xs text-faint">one-off</span>
                    )}
                  </TCell>
                  <TCell className="max-w-[320px] text-sm text-sub">
                    {lead.fitReason ?? lead.note ?? ""}
                  </TCell>
                  <TCell>
                    <FitMeter score={lead.fitScore} />
                  </TCell>
                  <TCell>
                    {lead.email ? (
                      lead.emailVerified ? (
                        <Badge tone="good">verified</Badge>
                      ) : (
                        <Badge>unverified</Badge>
                      )
                    ) : (
                      <Badge tone="warn">not found</Badge>
                    )}
                  </TCell>
                  <TCell>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpen(lead);
                      }}
                    >
                      Open
                    </Button>
                  </TCell>
                </TRow>
              ))}
            </tbody>
          </Table>
          {data && data.pagination.total_pages > 1 && (
            <div className="flex items-center justify-between pt-3">
              <Button
                size="sm"
                variant="ghost"
                disabled={!data.pagination.has_prev}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <span className="text-xs text-faint">
                Page {data.pagination.page} of {data.pagination.total_pages}
              </span>
              <Button
                size="sm"
                variant="ghost"
                disabled={!data.pagination.has_next}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          )}
          <p className="text-xs text-faint mt-3">
            Emails are only ever taken from a page the pipeline actually read — never guessed.
          </p>
        </>
      )}
    </div>
  );
}

export function FitMeter({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-faint">—</span>;
  return (
    <span
      className="inline-block h-1.5 w-16 rounded-full bg-panel2 align-middle"
      title={score.toFixed(2)}
    >
      <span
        className="block h-full rounded-full bg-accent"
        style={{ width: `${Math.round(Math.min(1, Math.max(0, score)) * 100)}%` }}
      />
    </span>
  );
}

function AddLeadForm({
  campaigns,
  onClose,
  onAdded,
  onOpen,
}: {
  campaigns: LeadCampaign[];
  onClose: () => void;
  onAdded: () => void;
  onOpen: (lead: Lead) => void;
}) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [campaignId, setCampaignId] = useState(campaigns[0]?.id ?? "");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [duplicateId, setDuplicateId] = useState<string | null>(null);

  const openDuplicate = async () => {
    if (!duplicateId) return;
    try {
      const lead = await api<Lead>(`/api/v1/lead-management/leads/${duplicateId}`);
      onOpen(lead);
    } catch {}
  };

  const save = async () => {
    if (!name.trim()) {
      setError("A lead needs at least a name.");
      return;
    }
    setSaving(true);
    setError(null);
    setDuplicateId(null);
    try {
      const res = await fetch("/api/v1/lead-management/leads", {
        method: "POST",
        headers: { ...siteHeader(), "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          sourceUrl: url.trim() || null,
          website: url.trim() || null,
          email: email.trim() || null,
          campaignId: campaignId || null,
          note: note.trim() || null,
        }),
      });
      const payload = await res.json().catch(() => ({}));
      if (res.status === 409) {
        const err = payload?.error ?? payload ?? {};
        const id =
          err.id ?? err.leadId ?? err.detail?.id ?? err.detail?.leadId ?? payload?.data?.id ?? null;
        setDuplicateId(typeof id === "string" ? id : null);
        setError("Already in your pipeline.");
        return;
      }
      if (!res.ok) {
        setError(payload?.error?.message ?? `Request failed (${res.status})`);
        return;
      }
      onAdded();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The lead did not save.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card className="mb-3 border-accent/30">
      <p className="text-xs font-medium uppercase tracking-wide text-faint mb-3">
        Add a lead yourself
      </p>
      <div className="flex flex-wrap gap-3">
        <div className="flex-1 min-w-[160px]">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Maya Chen" />
          </Field>
        </div>
        <div className="flex-1 min-w-[200px]">
          <Field label="Where you found them">
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="URL — their site, profile or post"
            />
          </Field>
        </div>
        <div className="flex-1 min-w-[160px]">
          <Field label="Email (optional)">
            <Input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Meelu can hunt it if empty"
            />
          </Field>
        </div>
        <div className="min-w-[170px]">
          <Field label="Campaign">
            <Select value={campaignId} onChange={(e) => setCampaignId(e.target.value)}>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
              <option value="">No campaign — one-off</option>
            </Select>
          </Field>
        </div>
      </div>
      <div className="mt-3">
        <Field label="Why them (optional)">
          <Input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Met at the expo — wants a sample for her April roundup"
          />
        </Field>
      </div>
      {error && (
        <p className="mt-3 text-sm text-bad">
          {error}{" "}
          {duplicateId && (
            <button
              type="button"
              className="text-accent hover:underline cursor-pointer"
              onClick={() => void openDuplicate()}
            >
              Open the existing lead
            </button>
          )}
        </p>
      )}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button size="sm" onClick={() => void save()} disabled={saving}>
          {saving ? "Saving…" : "Save lead"}
        </Button>
        <Button size="sm" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <p className="text-xs text-faint ml-auto">
          Saved as qualified — same pipeline as a discovered lead.
        </p>
      </div>
    </Card>
  );
}
