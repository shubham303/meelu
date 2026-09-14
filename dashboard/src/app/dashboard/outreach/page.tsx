"use client";

import { Suspense, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FileText, Megaphone, Pencil, Plus, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Button,
  Card,
  ConfirmDelete,
  EmptyState,
  IconButton,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { AgentLaunchButton, useAgentTasks } from "../agent-tasks";
import { useSendingAs } from "./sending-as";
import {
  emptyProjectForm,
  ProjectFormModal,
  projectToForm,
  type ProjectForm,
} from "./project-form-modal";
import { GuideButton } from "../guide/button";
import { cn, truncate } from "@/lib/utils";
import type { Campaign, OutreachProject } from "@/lib/types";

type Run = Campaign & { found: number };
import * as chips from "@/features/prompt-chips/outreach";

export default function OutreachPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <OutreachBody />
    </Suspense>
  );
}

function OutreachBody() {
  const router = useRouter();
  const focusId = useSearchParams().get("focus");
  const mailbox = useSendingAs();

  const {
    data: projects,
    loading: projectsLoading,
    error: projectsError,
    refresh: refreshProjects,
  } = useApi<OutreachProject[]>("/api/v1/outreach/projects?page_size=100");
  const { data: runs } = useApi<Run[]>("/api/v1/outreach/campaigns?page_size=100");

  const projectStats = useMemo(() => {
    const m = new Map<string, { runs: number; prospects: number }>();
    for (const r of runs ?? []) {
      const cur = m.get(r.projectId) ?? { runs: 0, prospects: 0 };
      cur.runs += 1;
      cur.prospects += r.found;
      m.set(r.projectId, cur);
    }
    return m;
  }, [runs]);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalKey, setModalKey] = useState(0);
  const [editingProject, setEditingProject] = useState<OutreachProject | null>(null);
  const [deleteProject, setDeleteProject] = useState<OutreachProject | null>(null);

  const { launchTask, updateTaskDraft } = useAgentTasks();
  const projectTaskRef = useRef<string | null>(null);
  const projectFormRef = useRef<ProjectForm>(emptyProjectForm);

  const openProjectModal = (t?: OutreachProject) => {
    setEditingProject(t ?? null);
    projectTaskRef.current = null;
    projectFormRef.current = t ? projectToForm(t) : emptyProjectForm;
    setModalKey((k) => k + 1);
    setModalOpen(true);
  };
  const closeProjectModal = () => {
    projectTaskRef.current = null;
    setModalOpen(false);
  };

  const deriveProjectDraft = (form: ProjectForm): Record<string, string> =>
    editingProject
      ? { project: `${editingProject.name} (id ${editingProject.id})`, ...form }
      : { ...form };

  return (
    <PageEnter>
      <PageHeader
        title="Outreach"
        description={
          "Any outreach — recruiting, partnerships, sales. Earning backlinks is one project type among them, which is why this desk is not called Links. Nothing sends without your say-so." +
          (mailbox.unknown ? "" : ` · ${mailbox.line}`)
        }
        actions={
          <>
            <GuideButton agent="outreach" />
            <Button onClick={() => openProjectModal()}>
              <Plus size={14} /> New project
            </Button>
          </>
        }
      />

      {projectsError && <p className="text-sm text-bad mb-4">{projectsError}</p>}

      {projectsLoading ? (
        <Spinner />
      ) : (projects ?? []).length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No projects yet"
          hint="A project is the standing brief — who to reach and what to say. Runs execute it. Start with one."
          action={
            <Button onClick={() => openProjectModal()}>
              <Plus size={14} /> New project
            </Button>
          }
        />
      ) : (
        <Stagger key="projects" className="grid gap-4 sm:grid-cols-2">
          {(projects ?? []).map((t) => {
            const stats = projectStats.get(t.id) ?? { runs: 0, prospects: 0 };
            return (
              <Card
                key={t.id}
                className={cn(
                  "stagger-item",
                  focusId === t.id && "border-accent ring-2 ring-accent/20",
                )}
                onClick={() => router.push(`/dashboard/outreach/projects/${t.id}`)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-medium text-ink truncate">{t.name}</p>
                    {t.goal && (
                      <p className="text-xs mt-1 truncate">
                        <span className="text-faint uppercase tracking-wide mr-1.5">
                          Goal
                        </span>
                        <span className="text-sub">{truncate(t.goal, 100)}</span>
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <IconButton
                      onClick={(e) => {
                        e.stopPropagation();
                        openProjectModal(t);
                      }}
                      aria-label="Edit project"
                    >
                      <Pencil size={14} />
                    </IconButton>
                    <IconButton
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteProject(t);
                      }}
                      aria-label="Delete project"
                    >
                      <Trash2 size={14} />
                    </IconButton>
                  </div>
                </div>
                <p className="text-sm text-sub mt-2">{truncate(t.prospectProfile, 160)}</p>
                <p className="flex items-center gap-1.5 text-xs text-sub mt-3">
                  <Megaphone size={12} className="text-faint" />
                  {stats.runs === 0
                    ? "Not run yet"
                    : `${stats.prospects} prospect${stats.prospects === 1 ? "" : "s"} · ${stats.runs} run${stats.runs === 1 ? "" : "s"}`}
                </p>
              </Card>
            );
          })}
        </Stagger>
      )}

      <ProjectFormModal
        key={modalKey}
        open={modalOpen}
        onClose={closeProjectModal}
        project={editingProject}
        onSaved={refreshProjects}
        onFormChange={(form) => {
          projectFormRef.current = form;
          if (projectTaskRef.current) {
            updateTaskDraft(projectTaskRef.current, deriveProjectDraft(form));
          }
        }}
        agentSlot={
          editingProject ? (
            <AgentLaunchButton
              title="Edit the brief with Meelu"
              hint="Starts a fresh task pinned to this project — describe the change and Meelu proposes the edit, saving only when you approve. Anything typed below counts as your draft; running tasks stay under Tasks at bottom-right."
              onClick={() => {
                const id = launchTask({
                  title: "Edit project",
                  endpoint: "/api/agent/edit-project",
                  emptyHint:
                    "Say what should change — “tighten the prospect profile to fintech newsletters only”, “rewrite the CTA” — or paste feedback and let Meelu propose the edit. Nothing is saved until you say so.",
                  suggestions: chips.projectEdit,
                  draft: deriveProjectDraft(projectFormRef.current),
                  onCreated: async () => {
                    if (projectTaskRef.current === id) {
                      projectTaskRef.current = null;
                      setModalOpen(false);
                    }
                    await refreshProjects();
                  },
                });
                projectTaskRef.current = id;
              }}
            />
          ) : (
            <AgentLaunchButton
              title="Draft the brief with Meelu"
              hint="Starts a fresh task that turns your description into a brief campaigns can execute, then saves it. Anything typed below is the starting draft; running tasks stay under Tasks at bottom-right."
              onClick={() => {
                const id = launchTask({
                  title: "Create project",
                  endpoint: "/api/agent/project",
                  emptyHint:
                    "Describe the outreach in a sentence — “sponsor freelance-finance newsletters to sell our tax tool” — or ask Meelu to sharpen the rough fields you filled in. It saves only when you say so.",
                  draft: { ...projectFormRef.current },
                  onCreated: async () => {
                    if (projectTaskRef.current === id) {
                      projectTaskRef.current = null;
                      setModalOpen(false);
                    }
                    await refreshProjects();
                  },
                });
                projectTaskRef.current = id;
              }}
            />
          )
        }
      />

      <ConfirmDelete
        open={deleteProject !== null}
        onClose={() => setDeleteProject(null)}
        what={deleteProject ? `project "${deleteProject.name}"` : "project"}
        onConfirm={async () => {
          if (!deleteProject) return;
          await api(`/api/v1/outreach/projects/${deleteProject.id}`, { method: "DELETE" });
          await refreshProjects();
        }}
      />
    </PageEnter>
  );
}
