"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import {
  Check,
  ChevronLeft,
  ListTodo,
  Maximize2,
  Minimize2,
  Paperclip,
  Sparkles,
  X,
} from "lucide-react";
import { gsap, useGSAP } from "@demo/components/animate";
import { IconButton } from "@demo/components/ui";
import { currentSiteId, GLOBAL } from "@demo/lib/current-site";
import { useApi, useCurrentSite } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { formatRelative } from "@demo/lib/utils";
import type { PromptChip } from "@demo/features/prompt-chips/lib";
import { taskModel } from "@demo/features/llm-models/models";
import { RunRail, useAgentRunsOptional } from "@demo/components/agent/run-rail";
import { AgentChat, type AgentChatItem } from "@demo/components/agent/agent-chat";
import { ChartFrame } from "@demo/components/agent/chart-frame";
import { PermissionPrompt } from "@demo/components/agent/permission-prompt";
import type { UserPromptSurface } from "@demo/features/user-prompts/api";
import { UserPromptEditor } from "@demo/features/user-prompts/prompt-editor";

declare global {
  interface Window {
    meeluAgent?: {
      runTurn: (payload: {
        action: string;
        siteId: string | null;
        message: string;
        sessionId?: string;
        form: Record<string, string | undefined>;
        params?: Record<string, string>;
        files?: Array<{ name: string; type: string; data: string }>;
        model?: string;
      }) => Promise<{ turnId?: string; error?: string }>;
      onEvent: (
        cb: (m: { turnId: string; event: string; data: Record<string, unknown> }) => void,
      ) => () => void;
      abort: (turnId: string) => void;
      sessionUsage?: () => Promise<{
        tokens: number;
        inputTokens: number;
        outputTokens: number;
        costUsd: number;
        turns: number;
        startedAt: number;
      }>;
      respondPermission?: (
        requestId: string,
        decision: "allow" | "always" | "full" | "deny",
      ) => Promise<{ ok?: boolean; error?: string }>;
      getConnectors?: () => Promise<ConnectorsView | { error: string }>;
      removeConnector?: (provider: string) => Promise<ConnectorsView | { error: string }>;
      connectGsc?: () => Promise<ConnectorsView | { error: string }>;
      connectGa4?: () => Promise<ConnectorsView | { error: string }>;
      getOwnKeys?: () => Promise<OwnKeysView | { error: string }>;
      saveOwnAnthropic?: (payload: {
        apiKey?: string;
        defaultModel?: string;
      }) => Promise<OwnKeysView | { error: string }>;
      ownModels?: () => Promise<{ models: OwnModel[] } | { error: string }>;
      saveTextFile?: (params: {
        name: string;
        content: string;
      }) => Promise<{ ok?: true; canceled?: true; path?: string } | { error: string }>;
      socialSignalsSearch?: (payload: {
        siteId: string;
        platforms?: string[];
      }) => Promise<{ jobId?: string; error?: string }>;
      socialSignalsStop?: (jobId: string) => Promise<{ stopping?: boolean; error?: string }>;
      socialSignalsActive?: (siteId: string) => Promise<SocialSignalsSnapshot | { error: string }>;
      socialSignalsPlatforms?: () => Promise<
        | { platforms: Array<{ id: string; label: string; access: "direct" | "apify"; available: boolean }> }
        | { error: string }
      >;
      onSocialSignalsEvent?: (
        cb: (m: { jobId: string; event: string; data: Record<string, unknown> }) => void,
      ) => () => void;
      findLeadsSearch?: (payload: { siteId: string; target?: number }) => Promise<{ jobId?: string; error?: string }>;
      findLeadsStop?: (jobId: string) => Promise<{ stopping?: boolean; error?: string }>;
      findLeadsActive?: (siteId: string) => Promise<FindLeadsSnapshot | { error: string }>;
      onFindLeadsEvent?: (
        cb: (m: { jobId: string; event: string; data: Record<string, unknown> }) => void,
      ) => () => void;
    };
  }
}

export type ConnectorsView = Record<
  string,
  { fields: Record<string, string>; updatedAt: string | null }
>;

export interface SocialSignalsSnapshot {
  jobId: string | null;
  stopping: boolean;
  startedAt: number | null;
  progress: Array<{ event: string; data: Record<string, unknown> }>;
}

export type FindLeadsSnapshot = SocialSignalsSnapshot;

export interface OwnKeysView {
  anthropic: { saved: boolean; defaultModel: string };
}

export interface OwnModel {
  id: string;
  name: string;
}

export type AgentTaskStatus = "idle" | "running" | "done" | "failed";

export interface AgentTaskInit {
  title: string;
  endpoint: string;
  emptyHint: string;
  draft: Record<string, string | undefined>;
  params?: Record<string, string>;
  suggestions?: PromptChip[];
  global?: boolean;
  autoStart?: string;
  promptSurface?: UserPromptSurface;
  onCreated?: () => void | Promise<void>;
  onWrote?: (tool: string) => void | Promise<void>;
}

interface AgentTask extends AgentTaskInit {
  id: string;
  createdAt: number;
  siteId: string | null;
  status: AgentTaskStatus;
}

interface AgentTasksApi {
  launchTask: (init: AgentTaskInit) => string;
  openTask: (id: string) => void;
  hasTask: (id: string) => boolean;
  updateTaskDraft: (id: string, draft: Record<string, string | undefined>) => void;
  updateTaskHooks: (id: string, hooks: Pick<AgentTaskInit, "onCreated" | "onWrote">) => void;
}

const AgentTasksContext = createContext<AgentTasksApi | null>(null);

export function useAgentTasks(): AgentTasksApi {
  const ctx = useContext(AgentTasksContext);
  if (!ctx) throw new Error("useAgentTasks needs <AgentTasksProvider> in the dashboard layout");
  return ctx;
}

export function AgentTasksProvider({ children }: { children: ReactNode }) {
  const isApp = useIsApp();
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [openTaskId, setOpenTaskId] = useState<string | null>(null);
  const [listOpen, setListOpen] = useState(false);
  const [lastTaskId, setLastTaskId] = useState<string | null>(null);
  const [instantId, setInstantId] = useState<string | null>(null);
  const [panelWidth, setPanelWidth] = useState(SHEET_DEFAULT);
  const [panelMaximized, setPanelMaximized] = useState(false);
  const tasksRef = useRef<AgentTask[]>([]);

  const { data: sites } = useApi<Array<{ id: string; name: string }>>("/api/v1/sites?page_size=100");
  const siteName = useCallback(
    (id: string | null) => (id ? (sites ?? []).find((s) => s.id === id)?.name : undefined),
    [sites],
  );

  const launchTask = useCallback(
    (init: AgentTaskInit): string => {
      if (!isApp) {
        if (process.env.NODE_ENV !== "production") {
          console.warn(
            `launchTask("${init.title}") was called on the web. The web frontend has no ` +
              "agent harness by design — gate the affordance that called this on useIsApp().",
          );
        }
        return "";
      }
      const id = crypto.randomUUID();
      const site = currentSiteId();
      setTasks((prev) => {
        const next = [
          ...prev,
          {
            ...init,
            id,
            createdAt: Date.now(),
            siteId: init.global || !site || site === GLOBAL ? null : site,
            status: "idle" as const,
          },
        ];
        tasksRef.current = next;
        return next;
      });
      setInstantId(null);
      setOpenTaskId(id);
      setLastTaskId(id);
      return id;
    },
    [isApp],
  );
  const openTask = useCallback((id: string) => {
    setInstantId(null);
    setOpenTaskId(id);
    setLastTaskId(id);
  }, []);
  const updateTaskDraft = useCallback(
    (id: string, draft: Record<string, string | undefined>) =>
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, draft } : t))),
    [],
  );
  const updateTaskHooks = useCallback(
    (id: string, hooks: Pick<AgentTaskInit, "onCreated" | "onWrote">) =>
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, ...hooks } : t))),
    [],
  );
  const switchTask = useCallback((id: string) => {
    setInstantId(id);
    setOpenTaskId(id);
    setLastTaskId(id);
  }, []);
  const hasTask = useCallback((id: string) => tasksRef.current.some((t) => t.id === id), []);
  const setTaskStatus = useCallback(
    (id: string, status: AgentTaskStatus) =>
      setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, status } : t))),
    [],
  );
  const removeTask = useCallback((id: string) => {
    setTasks((prev) => {
      const next = prev.filter((t) => t.id !== id);
      tasksRef.current = next;
      return next;
    });
    setOpenTaskId((prev) => (prev === id ? null : prev));
    setLastTaskId((prev) => (prev === id ? null : prev));
  }, []);

  const site = useCurrentSite();
  const here = site === GLOBAL ? null : site;
  const mine = useMemo(
    () => tasks.filter((t) => t.siteId === null || t.siteId === here),
    [tasks, here],
  );
  const mineIds = useMemo(() => new Set(mine.map((t) => t.id)), [mine]);

  const sorted = useMemo(
    () =>
      [...mine].sort((a, b) => {
        const ra = a.status === "running" ? 0 : 1;
        const rb = b.status === "running" ? 0 : 1;
        if (ra !== rb) return ra - rb;
        return b.createdAt - a.createdAt;
      }),
    [mine],
  );

  const rail = useAgentRunsOptional();
  const liveRuns = (rail?.runs ?? []).filter(
    (r) => r.status === "running" || r.status === "waiting",
  ).length;
  const needsYes = rail?.needsYes.length ?? 0;
  const anyRunning = mine.some((t) => t.status === "running") || liveRuns > 0;
  const dockCount = mine.length + liveRuns;

  const api = useMemo(
    () => ({ launchTask, openTask, hasTask, updateTaskDraft, updateTaskHooks }),
    [launchTask, openTask, hasTask, updateTaskDraft, updateTaskHooks],
  );

  return (
    <AgentTasksContext.Provider value={api}>
      {children}

      {isApp &&
        tasks.map((task) => (
        <AgentTaskChat
          key={task.id}
          title={task.title}
          endpoint={task.endpoint}
          emptyHint={task.emptyHint}
          draft={task.draft}
          params={task.params}
          suggestions={task.suggestions}
          autoStart={task.autoStart}
          promptSurface={task.promptSurface}
          siteId={task.siteId}
          open={openTaskId === task.id && mineIds.has(task.id)}
          instant={instantId === task.id}
          width={panelWidth}
          onWidthChange={setPanelWidth}
          maximized={panelMaximized}
          onMaximizedChange={setPanelMaximized}
          tabs={
            <TaskTabs
              tasks={mine}
              activeId={task.id}
              onPick={switchTask}
              onShowAll={() => {
                setInstantId(null);
                setOpenTaskId(null);
                setListOpen(true);
              }}
            />
          }
          onOpenChange={(o) => {
            if (!o) setInstantId(null);
            setOpenTaskId((prev) => (o ? task.id : prev === task.id ? null : prev));
          }}
          onStatus={(s) => setTaskStatus(task.id, s)}
          onCreated={async () => {
            await task.onCreated?.();
          }}
          onWrote={async (tool) => {
            await task.onWrote?.(tool);
          }}
        />
        ))}

      {isApp && dockCount > 0 && (
        <button
          type="button"
          onClick={() => setListOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full border border-edge2 bg-panel px-4 py-2.5 shadow-[0_6px_20px_rgb(31_45_61/0.10)] hover:border-accent/50 transition-colors cursor-pointer"
        >
          <ListTodo size={15} className="text-accent" />
          <span className="text-sm font-medium text-ink">Tasks</span>
          <span className="text-xs text-faint">{dockCount}</span>
          {needsYes > 0 ? (
            <span className="rounded-full bg-warn/15 px-1.5 py-px text-[10px] font-medium text-warn">
              {needsYes} needs you
            </span>
          ) : (
            anyRunning && (
              <span className="h-2 w-2 rounded-full bg-accent animate-pulse" aria-hidden />
            )
          )}
        </button>
      )}

      {isApp && (
      <TasksSheet
        open={listOpen}
        onClose={() => setListOpen(false)}
        tasks={sorted}
        siteName={siteName}
        onOpenTask={(id) => {
          setListOpen(false);
          setInstantId(null);
          setOpenTaskId(id);
          setLastTaskId(id);
        }}
        onRemoveTask={removeTask}
      />
      )}

      {isApp && lastTaskId !== null && mineIds.has(lastTaskId) && openTaskId === null && !listOpen && (
        <button
          type="button"
          onClick={() => {
            setInstantId(null);
            setOpenTaskId(lastTaskId);
          }}
          aria-label="Reopen last task panel"
          title="Reopen last task panel"
          className="fixed right-0 top-1/2 z-30 flex h-40 w-4 -translate-y-1/2 items-center justify-center rounded-l-lg border border-r-0 border-edge2 bg-panel/95 shadow-[0_2px_14px_rgb(31_45_61/0.10)] backdrop-blur-sm transition-colors hover:border-accent/50 hover:bg-panel cursor-pointer"
        >
          <ChevronLeft size={13} className="text-faint" />
        </button>
      )}
    </AgentTasksContext.Provider>
  );
}

function StatusSignal({ status }: { status: AgentTaskStatus }) {
  if (status === "running") {
    return <span className="h-2.5 w-2.5 rounded-full bg-accent animate-pulse shrink-0" aria-label="Running" />;
  }
  if (status === "failed") {
    return <span className="h-2.5 w-2.5 rounded-full bg-bad shrink-0" aria-label="Failed" />;
  }
  if (status === "done") {
    return <Check size={14} className="text-good shrink-0" aria-label="Done" />;
  }
  return <span className="h-2.5 w-2.5 rounded-full bg-edge2 shrink-0" aria-label="Waiting on you" />;
}

const STATUS_LABEL: Record<AgentTaskStatus, string> = {
  running: "running",
  idle: "your turn",
  done: "done",
  failed: "failed",
};

function TaskTabs({
  tasks,
  activeId,
  onPick,
  onShowAll,
}: {
  tasks: AgentTask[];
  activeId: string;
  onPick: (id: string) => void;
  onShowAll: () => void;
}) {
  const activeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
  }, [activeId]);

  if (tasks.length < 2) return null;
  return (
    <div className="flex items-center gap-1.5 border-b border-edge px-3 py-2">
      <div className="flex min-w-0 flex-1 gap-1.5 overflow-x-auto [scrollbar-width:none]">
        {tasks.map((task) => {
          const active = task.id === activeId;
          return (
            <button
              key={task.id}
              ref={active ? activeRef : undefined}
              type="button"
              onClick={() => !active && onPick(task.id)}
              aria-current={active ? "true" : undefined}
              title={`${task.title} · ${STATUS_LABEL[task.status]}`}
              className={`flex max-w-48 shrink-0 items-center gap-2 rounded-full border px-3 py-1 text-xs transition-colors ${
                active
                  ? "border-accent/50 bg-accent-soft text-accent"
                  : "border-edge bg-panel2/50 text-sub hover:border-accent/50 hover:text-ink cursor-pointer"
              }`}
            >
              <StatusSignal status={task.status} />
              <span className="truncate">{task.title}</span>
            </button>
          );
        })}
      </div>
      <IconButton onClick={onShowAll} aria-label="All tasks" title="All tasks">
        <ListTodo size={14} />
      </IconButton>
    </div>
  );
}

function TasksSheet({
  open,
  onClose,
  tasks,
  siteName,
  onOpenTask,
  onRemoveTask,
}: {
  open: boolean;
  onClose: () => void;
  tasks: AgentTask[];
  siteName: (id: string | null) => string | undefined;
  onOpenTask: (id: string) => void;
  onRemoveTask: (id: string) => void;
}) {
  const [closing, setClosing] = useState(false);
  const visible = open || closing;
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const close = () => {
    if (!open) return;
    setClosing(true);
    onClose();
  };

  useGSAP(
    () => {
      if (!panelRef.current) return;
      if (open) {
        gsap.fromTo(
          panelRef.current,
          { xPercent: 100 },
          { xPercent: 0, duration: 0.4, ease: "power3.out" },
        );
        gsap.fromTo(backdropRef.current, { opacity: 0 }, { opacity: 1, duration: 0.25 });
      } else if (closing) {
        gsap.to(panelRef.current, { xPercent: 100, duration: 0.3, ease: "power3.in" });
        gsap.to(backdropRef.current, {
          opacity: 0,
          duration: 0.25,
          onComplete: () => setClosing(false),
        });
      }
    },
    { dependencies: [open, closing] },
  );

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopImmediatePropagation();
        setClosing(true);
        onClose();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, onClose]);

  if (!visible || typeof document === "undefined") return null;
  return createPortal(
    <div className="fixed inset-0 z-[60]">
      <div
        ref={backdropRef}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
        onClick={close}
      />
      <div
        ref={panelRef}
        className="absolute right-0 top-0 h-full w-full max-w-sm bg-panel border-l border-edge2 flex flex-col will-change-transform"
      >
        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-edge">
          <ListTodo size={15} className="text-accent shrink-0" />
          <h2 className="font-display text-lg text-ink flex-1">Tasks</h2>
          <IconButton onClick={close} aria-label="Close">
            <X size={16} />
          </IconButton>
        </div>

        <RunRail className="border-b border-edge" onNavigate={close} />

        <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-1.5">
          {tasks.length === 0 && (
            <p className="text-sm text-faint px-2 py-4">
              No tasks yet — launch one from a ✳.
            </p>
          )}
          {tasks.map((task) => (
            <div
              key={task.id}
              role="button"
              tabIndex={0}
              onClick={() => onOpenTask(task.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onOpenTask(task.id);
              }}
              className="w-full flex items-center gap-3 rounded-lg border border-edge bg-panel2/50 px-3 py-2.5 text-left hover:border-accent/50 transition-colors cursor-pointer"
            >
              <StatusSignal status={task.status} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm text-ink truncate">{task.title}</span>
                <span className="block text-[11px] text-sub mt-0.5 truncate">
                  {STATUS_LABEL[task.status]}
                  {siteName(task.siteId) ? ` · ${siteName(task.siteId)}` : ""}
                  {" · "}
                  {formatRelative(new Date(task.createdAt).toISOString())}
                </span>
              </span>
              <button
                type="button"
                aria-label="Remove task"
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveTask(task.id);
                }}
                className="text-faint hover:text-bad transition-colors cursor-pointer shrink-0"
              >
                <X size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}

const SHEET_MIN = 360;
const SHEET_DEFAULT = 672;

type ChatItem =
  | { kind: "user"; text: string; files?: string[]; typed: boolean }
  | { kind: "assistant"; text: string }
  | { kind: "tool"; text: string; name?: string }
  | { kind: "chart"; html: string }
  | {
      kind: "permission";
      requestId: string;
      tool: string;
      input: Record<string, unknown>;
      answered?: "allow" | "always" | "full" | "deny";
    };

interface PendingFile {
  name: string;
  type: string;
  data: string;
}

const MAX_FILES = 5;
const MAX_FILE_BYTES = 2 * 1024 * 1024;

function AgentTaskChat({
  title,
  endpoint,
  emptyHint,
  draft,
  params,
  suggestions,
  autoStart,
  promptSurface,
  siteId,
  open,
  instant,
  width,
  onWidthChange,
  maximized,
  onMaximizedChange,
  tabs,
  onOpenChange,
  onStatus,
  onCreated,
  onWrote,
}: {
  title: string;
  endpoint: string;
  emptyHint: string;
  draft: Record<string, string | undefined>;
  params?: Record<string, string>;
  suggestions?: PromptChip[];
  autoStart?: string;
  promptSurface?: UserPromptSurface;
  siteId: string | null;
  open: boolean;
  instant: boolean;
  width: number;
  onWidthChange: (width: number) => void;
  maximized: boolean;
  onMaximizedChange: (maximized: boolean) => void;
  tabs: ReactNode;
  onOpenChange: (open: boolean) => void;
  onStatus: (status: AgentTaskStatus) => void;
  onCreated: () => void | Promise<void>;
  onWrote: (tool: string) => void | Promise<void>;
}) {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [files, setFiles] = useState<PendingFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savingPrompt, setSavingPrompt] = useState<string | null>(null);
  const sessionRef = useRef<string | null>(null);
  const abortRef = useRef<{ abort: () => void } | null>(null);
  const draftRef = useRef(draft);
  const onWroteRef = useRef(onWrote);
  useEffect(() => {
    draftRef.current = draft;
    onWroteRef.current = onWrote;
  });

  const [closing, setClosing] = useState(false);
  const visible = open || closing;
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ startX: number; startWidth: number; overshoot: number } | null>(null);

  const close = () => {
    if (!open) return;
    setClosing(true);
    onOpenChange(false);
  };

  useGSAP(
    () => {
      if (!panelRef.current) return;
      if (open && instant) {
        gsap.set(panelRef.current, { xPercent: 0, x: 0 });
        gsap.set(backdropRef.current, { opacity: 1 });
      } else if (open) {
        gsap.fromTo(
          panelRef.current,
          { xPercent: 100, x: 0 },
          { xPercent: 0, duration: 0.4, ease: "power3.out" },
        );
        gsap.fromTo(backdropRef.current, { opacity: 0 }, { opacity: 1, duration: 0.25 });
      } else if (closing) {
        gsap.to(panelRef.current, { xPercent: 100, duration: 0.3, ease: "power3.in" });
        gsap.to(backdropRef.current, {
          opacity: 0,
          duration: 0.25,
          onComplete: () => setClosing(false),
        });
      }
    },
    { dependencies: [open, closing] },
  );

  function onHandleDown(e: React.PointerEvent<HTMLDivElement>) {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { startX: e.clientX, startWidth: width, overshoot: 0 };
  }
  function onHandleMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!drag.current) return;
    const max = Math.floor(window.innerWidth * 0.85);
    const min = Math.min(SHEET_MIN, max);
    const desired = drag.current.startWidth + (drag.current.startX - e.clientX);
    onWidthChange(Math.min(Math.max(desired, min), max));
    const overshoot = Math.max(0, min - desired);
    drag.current.overshoot = overshoot;
    if (panelRef.current) gsap.set(panelRef.current, { x: overshoot });
  }
  function onHandleUp() {
    if (!drag.current) return;
    const { overshoot } = drag.current;
    drag.current = null;
    if (overshoot > 90) close();
    else if (panelRef.current) {
      gsap.to(panelRef.current, { x: 0, duration: 0.25, ease: "power3.out" });
    }
  }

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopImmediatePropagation();
        setClosing(true);
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [open, onOpenChange]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const autoStarted = useRef(false);
  useEffect(() => {
    if (!autoStart || autoStarted.current) return;
    const t = setTimeout(() => {
      autoStarted.current = true;
      void sendRef.current(autoStart);
    }, 0);
    return () => clearTimeout(t);
  }, [autoStart]);

  const push = (item: ChatItem) => setItems((prev) => [...prev, item]);
  const showProgress = (name: string, done: number, total: number) =>
    setItems((prev) => {
      const text = `${name} · ${done}/${total} reviewed`;
      const at = prev.findLastIndex((item) => item.kind === "tool" && item.name === name);
      if (at === -1) return [...prev, { kind: "tool", name, text }];
      return prev.map((item, i) => (i === at ? { kind: "tool", name, text } : item));
    });
  const appendAssistant = (text: string) =>
    setItems((prev) => {
      const last = prev[prev.length - 1];
      if (last?.kind === "assistant") {
        return [...prev.slice(0, -1), { kind: "assistant", text: last.text + text }];
      }
      return [...prev, { kind: "assistant", text }];
    });

  const sendRef = useRef(send);
  useEffect(() => {
    sendRef.current = send;
  });

  async function addFiles(list: FileList | null) {
    if (!list || list.length === 0) return;
    setError(null);
    const next = [...files];
    for (const f of Array.from(list)) {
      if (next.length >= MAX_FILES) {
        setError(`Up to ${MAX_FILES} files per message.`);
        break;
      }
      if (f.size > MAX_FILE_BYTES) {
        setError(`${f.name} is over ${Math.round(MAX_FILE_BYTES / 1024 / 1024)} MB.`);
        continue;
      }
      const bytes = new Uint8Array(await f.arrayBuffer());
      let binary = "";
      for (let i = 0; i < bytes.length; i += 0x8000) {
        binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      }
      next.push({ name: f.name, type: f.type || "text/plain", data: btoa(binary) });
    }
    setFiles(next);
  }

  async function answerPermission(
    requestId: string,
    decision: "allow" | "always" | "full" | "deny",
  ) {
    setItems((prev) =>
      prev.map((it) =>
        it.kind === "permission" && it.requestId === requestId
          ? { ...it, answered: decision }
          : it,
      ),
    );
    await window.meeluAgent?.respondPermission?.(requestId, decision);
  }

  async function send(text: string, displayAs?: string) {
    const message = text.trim() || (files.length > 0 ? "Use the attached file(s)." : "");
    if (!message || busy || done) return;
    const attachments = files;
    setFiles([]);
    setError(null);
    setBusy(true);
    onStatus("running");
    push({
      kind: "user",
      text: displayAs ?? message,
      files: attachments.map((f) => f.name),
      typed: displayAs === undefined && text.trim() !== "",
    });

    let created = false;
    let failed = false;
    let aborted = false;

    const handleEvent = (event: string, data: Record<string, unknown>) => {
      if (event === "session" && typeof data.sessionId === "string") {
        sessionRef.current = data.sessionId;
      } else if (event === "text" && typeof data.text === "string") {
        appendAssistant(data.text);
      } else if (event === "tool" && typeof data.name === "string") {
        push({ kind: "tool", text: data.name, name: data.name });
      } else if (
        event === "progress" &&
        typeof data.tool === "string" &&
        typeof data.done === "number" &&
        typeof data.total === "number"
      ) {
        showProgress(data.tool, data.done, data.total);
      } else if (event === "chart" && typeof data.html === "string") {
        push({ kind: "chart", html: data.html });
      } else if (event === "permission") {
        push({
          kind: "permission",
          requestId: String(data.requestId ?? ""),
          tool: String(data.tool ?? "this action"),
          input: (data.input as Record<string, unknown>) ?? {},
        });
      } else if (event === "created") {
        created = true;
      } else if (event === "wrote" && typeof data.tool === "string") {
        void onWroteRef.current(data.tool);
      } else if (event === "done") {
        if (!data.ok && typeof data.error === "string") {
          failed = true;
          setError(data.error);
        }
      }
    };

    try {
      const bridge = window.meeluAgent;
      if (!bridge) throw new Error("Agentic tasks run in the Meelu app.");
      {
        const action = endpoint.split("/").pop() ?? "";
        await new Promise<void>((resolve, reject) => {
          let turnId: string | null = null;
          const off = bridge.onEvent((m) => {
            if (turnId === null || m.turnId !== turnId) return;
            handleEvent(m.event, m.data);
            if (m.event === "done") {
              off();
              resolve();
            }
          });
          abortRef.current = {
            abort: () => {
              aborted = true;
              if (turnId) bridge.abort(turnId);
              off();
              resolve();
            },
          };
          bridge
            .runTurn({
              action,
              siteId,
              message,
              sessionId: sessionRef.current ?? undefined,
              form: draftRef.current,
              params,
              files: attachments.length > 0 ? attachments : undefined,
              model: taskModel() ?? undefined,
            })
            .then((res) => {
              if (res.error || !res.turnId) {
                off();
                reject(new Error(res.error ?? "The app could not start the task."));
                return;
              }
              turnId = res.turnId;
            })
            .catch((e) => {
              off();
              reject(e instanceof Error ? e : new Error(String(e)));
            });
        });
      }

      if (created) {
        setDone(true);
        await onCreated();
      }
    } catch (e) {
      if (!aborted) {
        failed = true;
        setError(e instanceof Error ? e.message : "Something went wrong");
      }
    } finally {
      setBusy(false);
      onStatus(created ? "done" : failed ? "failed" : "idle");
      abortRef.current = null;
    }
  }

  if (!visible || typeof document === "undefined") return null;

  const agentItems: AgentChatItem[] = items.map((item, i) => {
    if (item.kind === "user") {
      return { kind: "user", key: i, text: item.text, files: item.files, savable: item.typed };
    }
    if (item.kind === "assistant") return { kind: "assistant", key: i, text: item.text };
    if (item.kind === "tool") return { kind: "tool", key: i, text: item.text };
    if (item.kind === "chart") {
      return {
        kind: "custom",
        key: i,
        render: (
          <div className="overflow-hidden rounded-xl border border-edge bg-panel shadow-sm">
            <ChartFrame html={item.html} />
          </div>
        ),
      };
    }
    return {
      kind: "custom",
      key: i,
      render: (
        <PermissionPrompt item={item} onAnswer={(decision) => answerPermission(item.requestId, decision)} />
      ),
    };
  });

  return createPortal(
    <div className="fixed inset-0 z-[60]">
      <div
        ref={backdropRef}
        className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
        onClick={close}
      />
      <div
        ref={panelRef}
        style={maximized ? { width: "100vw" } : { width }}
        className="absolute right-0 top-0 h-full max-w-[85vw] bg-panel border-l border-edge2 flex flex-col will-change-transform"
      >
        {!maximized && (
          <div
            onPointerDown={onHandleDown}
            onPointerMove={onHandleMove}
            onPointerUp={onHandleUp}
            className="absolute left-0 top-0 z-10 h-full w-4 -translate-x-1/2 cursor-col-resize group flex items-center justify-center touch-none"
            aria-hidden
          >
            <div className="h-16 w-1 rounded-full bg-edge2 group-hover:bg-accent transition-colors" />
          </div>
        )}

        <div className="flex items-center gap-2.5 px-5 py-4 border-b border-edge">
          {done ? (
            <Check size={15} className="text-good shrink-0" />
          ) : (
            <Sparkles size={15} className="text-accent shrink-0" />
          )}
          <h2 className="font-display text-lg text-ink flex-1 truncate">{title}</h2>
          <IconButton
            onClick={() => onMaximizedChange(!maximized)}
            aria-label={maximized ? "Restore" : "Maximize"}
            title={maximized ? "Restore" : "Maximize"}
          >
            {maximized ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </IconButton>
          <IconButton onClick={close} aria-label="Close chat">
            <X size={16} />
          </IconButton>
        </div>

        {tabs}

        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            void addFiles(e.target.files);
            e.target.value = "";
          }}
        />

        <AgentChat
          className="flex-1 min-h-0 px-5 py-4"
          items={agentItems}
          busy={busy}
          thinkingLabel="Meelu is thinking"
          emptyState={<p className="text-sm text-faint">{emptyHint}</p>}
          chips={suggestions ?? []}
          onPickChip={(chip) => void send(chip.prompt, chip.label)}
          onSaveUserText={promptSurface ? setSavingPrompt : undefined}
          onSend={(text) => void send(text)}
          onStop={() => abortRef.current?.abort()}
          allowEmptySend={files.length > 0}
          placeholder="Tell Meelu what you want…"
          busyPlaceholder="Meelu is working…"
          onAttach={() => fileInputRef.current?.click()}
          attachmentsSlot={
            files.length > 0 ? (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {files.map((f, i) => (
                  <span
                    key={`${f.name}-${i}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-panel2 px-2.5 py-1 text-[11px] text-sub"
                  >
                    <Paperclip size={10} className="shrink-0" />
                    <span className="max-w-40 truncate">{f.name}</span>
                    <button
                      type="button"
                      aria-label={`Remove ${f.name}`}
                      onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                      className="text-faint hover:text-bad transition-colors cursor-pointer"
                    >
                      <X size={11} />
                    </button>
                  </span>
                ))}
              </div>
            ) : undefined
          }
          error={error}
          footer={
            done ? (
              <div>
                <p className="flex items-center gap-2 text-sm text-good">
                  <Check size={14} className="shrink-0" />
                  Task complete — this chat is closed.
                </p>
                <p className="text-xs text-faint mt-1">
                  Everything the task made is on the board. Start another action for the next
                  thing.
                </p>
              </div>
            ) : undefined
          }
          autoFocus
        />
      </div>
      {promptSurface && (
        <UserPromptEditor
          open={savingPrompt !== null}
          onClose={() => setSavingPrompt(null)}
          surface={promptSurface}
          initialPrompt={savingPrompt ?? ""}
          elevated
        />
      )}
    </div>,
    document.body,
  );
}

export function AgentLaunchButton({
  title,
  hint,
  onClick,
}: {
  title: string;
  hint: string;
  onClick: () => void;
}) {
  const isApp = useIsApp();
  if (!isApp) return null;
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-2.5 rounded-lg border border-accent/30 bg-accent-soft px-3 py-2.5 text-left transition-colors hover:border-accent/50 cursor-pointer"
    >
      <Sparkles size={15} className="text-accent shrink-0" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm text-accent font-medium">{title}</span>
        <span className="block text-xs text-sub">{hint}</span>
      </span>
    </button>
  );
}

export async function runInlineTurn({
  action,
  message,
  form,
}: {
  action: string;
  message: string;
  form?: Record<string, string | undefined>;
}): Promise<string> {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  if (!bridge) throw new Error("Meelu drafts on your device — open this in the Meelu app.");

  const site = currentSiteId();
  let text = "";

  await new Promise<void>((resolve, reject) => {
    let turnId: string | null = null;
    const off = bridge.onEvent((m) => {
      if (turnId === null || m.turnId !== turnId) return;
      if (m.event === "text" && typeof m.data.text === "string") text += m.data.text;
      if (m.event === "done") {
        off();
        if (!m.data.ok && typeof m.data.error === "string") reject(new Error(m.data.error));
        else resolve();
      }
    });
    bridge
      .runTurn({
        action,
        siteId: site && site !== GLOBAL ? site : null,
        message,
        form: form ?? {},
        model: taskModel() ?? undefined,
      })
      .then((res) => {
        if (res.error || !res.turnId) {
          off();
          reject(new Error(res.error ?? "The app could not start the draft."));
          return;
        }
        turnId = res.turnId;
      })
      .catch((err) => {
        off();
        reject(err instanceof Error ? err : new Error(String(err)));
      });
  });

  return text.trim();
}
