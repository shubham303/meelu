"use client";

import { useState, type ReactNode } from "react";
import { Button, Field, Input, Modal, Textarea } from "@/components/ui";
import { api } from "@/lib/use-api";
import type { OutreachProject } from "@/lib/types";

export interface ProjectForm {
  name: string;
  goal: string;
  prompt: string;
  prospectProfile: string;
  searchCriteria: string;
  emailTone: string;
  valueProp: string;
  cta: string;
}

export const emptyProjectForm: ProjectForm = {
  name: "",
  goal: "",
  prompt: "",
  prospectProfile: "",
  searchCriteria: "",
  emailTone: "",
  valueProp: "",
  cta: "",
};

export function projectToForm(t: OutreachProject): ProjectForm {
  return {
    name: t.name,
    goal: t.goal ?? "",
    prompt: t.prompt ?? "",
    prospectProfile: t.prospectProfile,
    searchCriteria: t.searchCriteria ?? "",
    emailTone: t.emailTone ?? "",
    valueProp: t.valueProp ?? "",
    cta: t.cta ?? "",
  };
}

export function ProjectFormModal({
  open,
  onClose,
  project,
  onSaved,
  agentSlot,
  onFormChange,
}: {
  open: boolean;
  onClose: () => void;
  project: OutreachProject | null;
  onSaved: () => void | Promise<void>;
  agentSlot?: ReactNode;
  onFormChange?: (form: ProjectForm) => void;
}) {
  const [form, setForm] = useState<ProjectForm>(
    project ? projectToForm(project) : emptyProjectForm,
  );
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const setTf = (patch: Partial<ProjectForm>) => {
    const next = { ...form, ...patch };
    setForm(next);
    onFormChange?.(next);
  };

  const save = async () => {
    setBusy(true);
    setErr(null);
    try {
      if (project) {
        await api(`/api/v1/outreach/projects/${project.id}`, { method: "PUT", body: form });
      } else {
        await api("/api/v1/outreach/projects", { method: "POST", body: form });
      }
      onClose();
      await onSaved();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={project ? "Edit project" : "New project"}
      wide
    >
      <div className="space-y-4">
        {agentSlot}
        <Field label="Name">
          <Input
            value={form.name}
            onChange={(e) => setTf({ name: e.target.value })}
            placeholder="What this outreach push is called, e.g. Guest-post partners"
            autoFocus
          />
        </Field>
        <Field label="Goal">
          <Input
            value={form.goal}
            onChange={(e) => setTf({ goal: e.target.value })}
            placeholder="What a successful campaign achieves, e.g. guest posts on finance blogs"
          />
        </Field>
        <Field label="Prompt">
          <Textarea
            rows={4}
            value={form.prompt}
            onChange={(e) => setTf({ prompt: e.target.value })}
            placeholder="The standing instruction every campaign run executes: what to find, how to verify someone is a real fit, and what the first email should do."
          />
        </Field>
        <Field label="Prospect profile">
          <Textarea
            value={form.prospectProfile}
            onChange={(e) => setTf({ prospectProfile: e.target.value })}
            placeholder="Who to look for: the audience they serve and the kind of site or community they run. Naming 2–3 real examples ('like X and Y') sharpens the search more than adjectives."
          />
        </Field>
        <Field label="Search criteria">
          <Input
            value={form.searchCriteria}
            onChange={(e) => setTf({ searchCriteria: e.target.value })}
            placeholder="Where and how to search: platforms or directories to check, search phrases, filters like region or size"
          />
        </Field>
        <Field label="Email tone">
          <Input
            value={form.emailTone}
            onChange={(e) => setTf({ emailTone: e.target.value })}
            placeholder="How every email should sound, e.g. warm, brief, peer-to-peer — no marketing speak"
          />
        </Field>
        <Field label="Value prop">
          <Input
            value={form.valueProp}
            onChange={(e) => setTf({ valueProp: e.target.value })}
            placeholder="What's in it for the prospect — the one thing the email offers them, from their point of view"
          />
        </Field>
        <Field label="Call to action">
          <Input
            value={form.cta}
            onChange={(e) => setTf({ cta: e.target.value })}
            placeholder="The single small ask that ends the email — easy to say yes to, e.g. reply for a draft outline"
          />
        </Field>
        {err && <p className="text-sm text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={save}
            disabled={busy || !form.name.trim() || !form.prospectProfile.trim()}
          >
            {project ? "Save changes" : "Create project"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
