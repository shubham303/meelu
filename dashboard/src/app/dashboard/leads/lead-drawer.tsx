"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Badge, Button, ConfirmDelete, Drawer, Field, Select, Textarea } from "@/components/ui";
import { api } from "@/lib/use-api";
import type { Lead, LeadStage } from "@/lib/types";
import { sourceLabel, STAGE_LABEL, STAGE_TONE, STAGES } from "./lib";

export function LeadDrawer({
  lead,
  campaignName,
  onClose,
  onSaved,
}: {
  lead: Lead | null;
  campaignName: (id: string | null) => string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [note, setNote] = useState("");
  const [seeded, setSeeded] = useState(false);
  const [busy, setBusy] = useState<"note" | "stage" | "delete" | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [lastLeadId, setLastLeadId] = useState<string | null>(null);
  if ((lead?.id ?? null) !== lastLeadId) {
    setLastLeadId(lead?.id ?? null);
    setNote(lead?.note ?? "");
    setSeeded(lead !== null);
    setError(null);
    setBusy(null);
    setConfirming(false);
  }
  if (lead && !seeded) {
    setSeeded(true);
    setNote(lead.note ?? "");
  }

  const saveNote = async () => {
    if (!lead) return;
    setBusy("note");
    setError(null);
    try {
      await api(`/api/v1/lead-management/leads/${lead.id}`, {
        method: "PATCH",
        body: { note: note.trim() || null },
      });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The note did not save.");
    } finally {
      setBusy(null);
    }
  };

  const changeStage = async (stage: LeadStage) => {
    if (!lead) return;
    setBusy("stage");
    setError(null);
    try {
      await api(`/api/v1/lead-management/leads/${lead.id}`, { method: "PATCH", body: { stage } });
      onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The stage did not change.");
    } finally {
      setBusy(null);
    }
  };

  const remove = async () => {
    if (!lead) return;
    setBusy("delete");
    setError(null);
    try {
      await api(`/api/v1/lead-management/leads/${lead.id}`, { method: "DELETE" });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The lead did not delete.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Drawer
      open={lead !== null}
      onClose={onClose}
      title={
        lead ? (
          <div>
            <h2 className="font-display text-lg text-ink">{lead.name}</h2>
            <p className="text-xs text-faint mt-0.5">
              {[lead.company, lead.role].filter(Boolean).join(" · ")}{" "}
              <Badge tone={STAGE_TONE[lead.stage]} className="align-middle ml-1">
                {lead.stage}
              </Badge>
            </p>
          </div>
        ) : undefined
      }
    >
      {lead && (
        <div className="space-y-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">
              Why they fit — evidence from the run
            </p>
            {lead.evidence.length > 0 ? (
              <div className="space-y-2">
                {lead.evidence.map((e, i) => (
                  <blockquote
                    key={i}
                    className="border-l-2 border-edge2 pl-3 text-[13px] text-sub"
                  >
                    &ldquo;{e.quote}&rdquo;{" "}
                    {e.url && (
                      <a
                        href={e.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-accent hover:underline"
                      >
                        source
                      </a>
                    )}
                  </blockquote>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-sub">{lead.fitReason ?? lead.note ?? "No evidence recorded."}</p>
            )}
            <div className="mt-2.5 flex flex-wrap gap-1.5">
              {lead.fitScore != null && (
                <Badge tone="accent">fit {lead.fitScore.toFixed(2)}</Badge>
              )}
              <Badge>source: {sourceLabel(lead.source)}</Badge>
              {lead.email &&
                (lead.emailVerified ? (
                  <Badge tone="good">email verified on their page</Badge>
                ) : (
                  <Badge>email unverified</Badge>
                ))}
              {!lead.email && <Badge tone="warn">no email found</Badge>}
              {campaignName(lead.campaignId) && <Badge>{campaignName(lead.campaignId)}</Badge>}
            </div>
            {(lead.website || lead.sourceUrl) && (
              <a
                href={lead.website ?? lead.sourceUrl ?? "#"}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-[13px] text-accent hover:underline"
              >
                <ExternalLink size={12} /> {lead.website ?? lead.sourceUrl}
              </a>
            )}
          </div>

          {lead.email && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-faint mb-1">Email</p>
              <p className="text-[13px] text-ink">{lead.email}</p>
            </div>
          )}

          <div>
            <Field label="Note" hint="Anything worth remembering about this lead.">
              <Textarea rows={4} value={note} onChange={(e) => setNote(e.target.value)} />
            </Field>
            <Button
              size="sm"
              variant="outline"
              className="mt-2"
              onClick={() => void saveNote()}
              disabled={busy !== null}
            >
              {busy === "note" ? "Saving…" : "Save note"}
            </Button>
          </div>

          {error && <p className="text-sm text-bad">{error}</p>}

          <div className="flex flex-wrap items-center gap-2">
            <Select
              className="w-auto"
              value={lead.stage}
              disabled={busy !== null}
              onChange={(e) => void changeStage(e.target.value as LeadStage)}
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>
                  Stage: {STAGE_LABEL[s]}
                </option>
              ))}
            </Select>
            <Button
              size="sm"
              variant="ghost"
              className="ml-auto text-bad"
              disabled={busy !== null}
              onClick={() => setConfirming(true)}
            >
              Delete lead
            </Button>
          </div>
          <ConfirmDelete
            open={confirming}
            onClose={() => setConfirming(false)}
            onConfirm={remove}
            what={`the "${lead.name}" lead`}
          />
        </div>
      )}
    </Drawer>
  );
}
