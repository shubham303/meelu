"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, ChevronsUpDown, Globe, Layers, Plus, Trash2 } from "lucide-react";
import { Button, Field, IconButton, Input, Modal } from "@demo/components/ui";
import { bridge } from "@demo/components/agent/bridge";
import { GLOBAL_HOME, SITE_ROOT, WEBSITE_HOME } from "@demo/components/desks";
import { GLOBAL, setCurrentSite } from "@demo/lib/current-site";
import { api, useApi, useCurrentSite } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";
import { MCP_CATALOG } from "@demo/lib/mcp-catalog";
import type { SiteProfile } from "@demo/lib/types";

function pausedTitle(deletesAt: string | null | undefined): string {
  if (!deletesAt) return "Paused: the workspace ran out of credits";
  const day = new Date(deletesAt).toLocaleDateString(undefined, { dateStyle: "medium" });
  return `Paused: the workspace ran out of credits. Add credits before ${day} or this website is deleted.`;
}

function PausedTag({ deletesAt }: { deletesAt?: string | null }) {
  return (
    <span
      title={pausedTitle(deletesAt)}
      className="shrink-0 rounded border border-warn/40 bg-warn/10 px-1 text-[10px] leading-4 text-warn"
    >
      paused
    </span>
  );
}

export function SiteSwitcher() {
  const { data: sites, refresh } = useApi<SiteProfile[]>("/api/v1/sites?page_size=100");
  const router = useRouter();
  const isApp = useIsApp();
  const currentId = useCurrentSite();
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [deleting, setDeleting] = useState<SiteProfile | null>(null);

  const list = useMemo(() => sites ?? [], [sites]);
  const global = currentId === GLOBAL;
  const current = global ? null : (list.find((s) => s.id === currentId) ?? list[0] ?? null);

  useEffect(() => {
    if (!global && current && current.id !== currentId) setCurrentSite(current.id);
  }, [global, current, currentId]);

  const added = useCallback(
    async (site: SiteProfile) => {
      await refresh();
      setCurrentSite(site.id);
      router.push(SITE_ROOT);
    },
    [refresh, router],
  );

  const pick = useCallback(
    (id: string) => {
      setOpen(false);
      if (id === currentId) return;
      setCurrentSite(id);
      router.push(id === GLOBAL ? GLOBAL_HOME : WEBSITE_HOME);
    },
    [currentId, router],
  );

  if (list.length === 0) {
    return (
      <div className="px-2 pb-3">
        <Button size="sm" className="w-full" onClick={() => setAdding(true)}>
          <Plus size={14} /> Add a website
        </Button>
        {adding && (
          <AddSiteModal isApp={isApp} onClose={() => setAdding(false)} onAdded={added} />
        )}
      </div>
    );
  }

  return (
    <div className="px-2 pb-3 relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 rounded-lg border border-edge bg-panel2 px-2.5 py-2 text-left hover:border-edge2 transition-colors cursor-pointer"
      >
        {global ? (
          <Layers size={14} className="text-sub shrink-0" />
        ) : (
          <Globe size={14} className="text-accent shrink-0" />
        )}
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <span className="block text-sm text-ink truncate">
              {global ? "Global" : current?.name}
            </span>
            {current?.status === "disabled" && <PausedTag deletesAt={current.deletesAt} />}
          </span>
          <span className="block text-[11px] text-faint truncate">
            {global ? "not about one website" : current?.domain}
          </span>
        </span>
        <ChevronsUpDown size={13} className="text-faint shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute left-2 right-2 z-40 mt-1 rounded-lg border border-edge bg-panel shadow-lg overflow-hidden">
            <ul className="max-h-64 overflow-y-auto py-1">
              <li className="border-b border-edge">
                <button
                  onClick={() => pick(GLOBAL)}
                  className={cn(
                    "w-full flex items-center gap-2 px-2.5 py-2 text-left hover:bg-panel2 transition-colors cursor-pointer",
                    global && "bg-accent-soft",
                  )}
                >
                  <Check size={13} className={cn("shrink-0", global ? "text-accent" : "opacity-0")} />
                  <span className="min-w-0">
                    <span className="block text-sm text-ink">Global</span>
                    <span className="block text-[11px] text-faint truncate">
                      Activity
                    </span>
                  </span>
                </button>
              </li>
              {list.map((site) => (
                <li key={site.id} className="group flex items-center">
                  <button
                    onClick={() => pick(site.id)}
                    className={cn(
                      "flex min-w-0 flex-1 items-center gap-2 px-2.5 py-2 text-left hover:bg-panel2 transition-colors cursor-pointer",
                      site.id === current?.id && "bg-accent-soft",
                    )}
                  >
                    <Check
                      size={13}
                      className={cn(
                        "shrink-0",
                        site.id === current?.id ? "text-accent" : "opacity-0",
                      )}
                    />
                    <span className="min-w-0">
                      <span className="flex items-center gap-1.5">
                        <span className="block text-sm text-ink truncate">{site.name}</span>
                        {site.status === "disabled" && <PausedTag deletesAt={site.deletesAt} />}
                      </span>
                      <span className="block text-[11px] text-faint truncate">{site.domain}</span>
                    </span>
                  </button>
                  <IconButton
                    aria-label={`Delete ${site.name}`}
                    title="Delete — this cannot be undone"
                    className="mr-1.5 shrink-0 opacity-0 group-hover:opacity-100 hover:text-bad"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleting(site);
                    }}
                  >
                    <Trash2 size={13} />
                  </IconButton>
                </li>
              ))}
            </ul>
            <button
              onClick={() => {
                setOpen(false);
                setAdding(true);
              }}
              className="w-full flex items-center gap-2 border-t border-edge px-2.5 py-2 text-sm text-sub hover:text-ink hover:bg-panel2 transition-colors cursor-pointer"
            >
              <Plus size={13} /> Add a website
            </button>
          </div>
        </>
      )}

      {adding && <AddSiteModal isApp={isApp} onClose={() => setAdding(false)} onAdded={added} />}

      <DeleteSiteModal
        site={deleting}
        onClose={() => setDeleting(null)}
        onDeleted={async () => {
          await refresh();
          if (deleting && deleting.id === currentId) setCurrentSite(GLOBAL);
        }}
      />
    </div>
  );
}

function DeleteSiteModal({
  site,
  onClose,
  onDeleted,
}: {
  site: SiteProfile | null;
  onClose: () => void;
  onDeleted: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  return (
    <Modal open={!!site} onClose={onClose} title={site ? `Delete ${site.name}?` : "Delete?"}>
      <div className="space-y-4">
        <p className="text-sm text-sub">
          Everything under {site?.name} goes with it — pages, content, social posts, notes
          and crawls. This cannot be undone; to work on {site?.domain} again you would add it back
          and crawl it from scratch.
        </p>
        {err && <p className="text-sm text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="danger"
            disabled={busy}
            onClick={async () => {
              if (!site) return;
              setBusy(true);
              setErr(null);
              try {
                await api(`/api/v1/sites/${site.id}`, { method: "DELETE" });
                await onDeleted();
                onClose();
              } catch (e) {
                setErr(e instanceof Error ? e.message : "Something went wrong");
              } finally {
                setBusy(false);
              }
            }}
          >
            <Trash2 size={14} /> Delete
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function AddSiteModal({
  isApp,
  onClose,
  onAdded,
}: {
  isApp: boolean;
  onClose: () => void;
  onAdded: (site: SiteProfile) => Promise<void> | void;
}) {
  const [domain, setDomain] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  async function save() {
    if (!domain.trim() || !name.trim()) {
      setErr("Both the domain and a name, please.");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      const site = await api<SiteProfile>("/api/v1/sites", {
        method: "POST",
        body: { domain, name },
      });
      if (isApp) void bridge()?.describeSite?.(site.id);
      await onAdded(site);
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not add that website");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open onClose={onClose} title="Add a website">
      <div className="space-y-4">
        <p className="text-sm text-sub">
          A second business is a second website, not a second account. Its projects, posts,
          content and pages stay entirely separate — only your profile and saved prompts are shared.
        </p>
        <Field label="Website" hint="The host it serves on, www and all: www.example.com">
          <Input
            autoFocus
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="www.example.com"
          />
        </Field>
        <Field label="Business name">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Example Co" />
        </Field>
        <p className="text-xs text-faint">
          A website costs 0.5 credits a day, charged when you add it and every 24 hours after.
          It pauses if the balance runs out and picks up again once you top up.
        </p>
        <p className="text-xs text-faint">
          {isApp
            ? "That's all we need — your coworker reads the homepage and writes up what the site is about in the background, and the crawl starts from the Site desk."
            : "Next you'll crawl it from the Site desk. In the Meelu app your coworker then writes up what the site is about."}
        </p>
        {err && <p className="text-sm text-bad">{err}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={busy} onClick={() => void save()}>
            Add
          </Button>
        </div>
      </div>
    </Modal>
  );
}

