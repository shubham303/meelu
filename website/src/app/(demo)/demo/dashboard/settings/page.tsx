"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  Check,
  Copy,
  Cpu,
  KeyRound,
  LogOut,
  Plug,
  Plus,
  Sparkles,
  Trash2,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import {
  Button,
  Card,
  ConfirmDelete,
  Field,
  IconButton,
  Input,
  PageHeader,
  Spinner,
  Textarea,
  Table,
  TCell,
  THead,
  TRow,
} from "@demo/components/ui";
import { meeluConfigJson } from "@demo/lib/mcp-catalog";
import { GLOBAL, setCurrentSite } from "@demo/lib/current-site";
import { api, useApi, useCurrentSite } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { formatRelative } from "@demo/lib/utils";
import { signOut, useSession } from "@demo/lib/session";
import { subscribeToUsage, usageServerSnapshot, usageSnapshot } from "@demo/lib/session-usage";
import type { ApiKey, CreatedApiKey, UserProfile } from "@demo/lib/types";
import * as chips from "@demo/features/prompt-chips/profile";
import { useAgentTasks } from "../agent-tasks";
import { AppUpdateCard } from "./app-update-card";

function SectionHeader({ icon: Icon, title, hint }: { icon: LucideIcon; title: string; hint?: string }) {
  return (
    <div className="mb-4">
      <h2 className="font-display text-lg text-ink flex items-center gap-2">
        <Icon size={16} className="text-accent" /> {title}
      </h2>
      {hint && <p className="text-sm text-sub mt-1 max-w-2xl">{hint}</p>}
    </div>
  );
}

export default function SettingsPage() {
  const global = useCurrentSite() === GLOBAL;
  const isApp = useIsApp();
  const keysApi = useApi<ApiKey[]>("/api/v1/keys?page_size=100");

  return (
    <PageEnter>
      <PageHeader
        title="Settings"
        description={
          isApp
            ? "Websites, model and connectors."
            : global
              ? "Your coworker connection and workspace housekeeping. Pick a website to edit its profile."
              : "Your site profile, coworker connection, and workspace housekeeping."
        }
      />
      <Stagger className="space-y-5">
        {!isApp && (
          <McpSection
            keys={keysApi.data ?? []}
            loading={keysApi.loading}
            error={keysApi.error}
            refresh={keysApi.refresh}
          />
        )}
        <ProfileSection />
        <AccountSection />
        {isApp && <ModelUsageSection />}
        {isApp && <AppUpdateCard />}
      </Stagger>
    </PageEnter>
  );
}

function ProfileSection() {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const { data, loading, refresh } = useApi<UserProfile | null>("/api/v1/profile");

  const [form, setForm] = useState({
    fullName: "",
    role: "",
    company: "",
    timezone: "",
    signature: "",
    writingVoice: "",
    bio: "",
    linkedinUrl: "",
    xUrl: "",
    websiteUrl: "",
  });
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (dirty) return;
    setForm({
      fullName: data?.fullName ?? "",
      role: data?.role ?? "",
      company: data?.company ?? "",
      timezone: data?.timezone ?? "",
      signature: data?.signature ?? "",
      writingVoice: data?.writingVoice ?? "",
      bio: data?.bio ?? "",
      linkedinUrl: data?.linkedinUrl ?? "",
      xUrl: data?.xUrl ?? "",
      websiteUrl: data?.websiteUrl ?? "",
    });
  }, [data, dirty]);

  const set = (k: keyof typeof form) => (v: string) => {
    setDirty(true);
    setSaved(false);
    setForm((f) => ({ ...f, [k]: v }));
  };

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await api("/api/v1/profile", {
        method: "PUT",
        body: {
          fullName: form.fullName.trim(),
          role: form.role.trim(),
          company: form.company.trim(),
          timezone: form.timezone.trim(),
          signature: form.signature,
          writingVoice: form.writingVoice.trim(),
          bio: form.bio.trim(),
          linkedinUrl: form.linkedinUrl.trim(),
          xUrl: form.xUrl.trim(),
          websiteUrl: form.websiteUrl.trim(),
        },
      });
      setDirty(false);
      setSaved(true);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save your profile.");
    } finally {
      setSaving(false);
    }
  }

  const openAsk = () => {
    launchTask({
      title: "Set up your profile",
      endpoint: "/api/agent/profile-setup",
      emptyHint: "Tell Meelu who you are — or press a chip and it will ask.",
      suggestions: chips.setup,
      draft: {},
      global: true,
      onCreated: () => void refresh(),
    });
  };

  const blank = !loading && !form.signature.trim() && !form.writingVoice.trim();

  return (
    <Card className="stagger-item">
      <div className="flex items-start justify-between gap-3">
        <SectionHeader
          icon={UserRound}
          title="You"
          hint="Who Meelu writes as. Your voice steers what it drafts."
        />
        {isApp && (
          <IconButton
            title="Set this up with Meelu"
            aria-label="Set this up with Meelu"
            className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent shrink-0"
            onClick={openAsk}
          >
            <Sparkles size={16} />
          </IconButton>
        )}
      </div>

      {loading ? (
        <Spinner className="py-6" />
      ) : (
        <>
          {blank && (
            <p className="text-sm text-sub mb-4">
              Nothing here yet, so content is written in no
              particular voice.{" "}
              {isApp ? "Fill this in, or press ✳ and Meelu will ask." : "Fill this in below."}
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Your name">
              <Input
                value={form.fullName}
                onChange={(e) => set("fullName")(e.target.value)}
                placeholder="e.g. Shubham Randive"
              />
            </Field>
            <Field label="Role" hint="How you're introduced.">
              <Input
                value={form.role}
                onChange={(e) => set("role")(e.target.value)}
                placeholder="e.g. Founder"
              />
            </Field>
            <Field label="Company">
              <Input
                value={form.company}
                onChange={(e) => set("company")(e.target.value)}
                placeholder="e.g. Meelu"
              />
            </Field>
            <Field label="Timezone" hint='An IANA name — "Asia/Kolkata", not "IST".'>
              <Input
                value={form.timezone}
                onChange={(e) => set("timezone")(e.target.value)}
                placeholder="e.g. Asia/Kolkata"
              />
            </Field>
          </div>

          <div className="mt-4 space-y-4">
            <Field label="Sign-off" hint="Used verbatim at the bottom of emails Meelu drafts — line breaks and all.">
              <Textarea
                rows={3}
                value={form.signature}
                onChange={(e) => set("signature")(e.target.value)}
                placeholder={"Thanks,\nShubham"}
              />
            </Field>
            <Field label="How you want to come across" hint="In your own words.">
              <Textarea
                rows={3}
                value={form.writingVoice}
                onChange={(e) => set("writingVoice")(e.target.value)}
                placeholder="e.g. Plain-spoken and direct. Short sentences, no jargon, never salesy."
              />
            </Field>
            <Field
              label="Short bio"
              hint="A line or two about you — what a stranger reading a cold email would want to know."
            >
              <Textarea
                rows={3}
                value={form.bio}
                onChange={(e) => set("bio")(e.target.value)}
                placeholder="e.g. Built and sold two small SaaS products. Now working on Meelu full time."
              />
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 mt-4">
            <Field label="LinkedIn">
              <Input
                value={form.linkedinUrl}
                onChange={(e) => set("linkedinUrl")(e.target.value)}
                placeholder="linkedin.com/in/you"
              />
            </Field>
            <Field label="X">
              <Input
                value={form.xUrl}
                onChange={(e) => set("xUrl")(e.target.value)}
                placeholder="x.com/you"
              />
            </Field>
            <Field label="Your own site" hint="Personal, not the business.">
              <Input
                value={form.websiteUrl}
                onChange={(e) => set("websiteUrl")(e.target.value)}
                placeholder="you.com"
              />
            </Field>
          </div>

          {error && <p className="text-sm text-bad mt-3">{error}</p>}

          <div className="flex items-center gap-3 mt-4">
            <Button disabled={saving || !dirty} onClick={() => void save()}>
              {saving ? "Saving…" : "Save"}
            </Button>
            {saved && !dirty && (
              <span className="text-sm text-sub flex items-center gap-1.5">
                <Check size={14} className="text-good" /> Saved
              </span>
            )}
          </div>
        </>
      )}
    </Card>
  );
}

function McpSection({
  keys,
  loading,
  error,
  refresh,
}: {
  keys: ApiKey[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}) {
  const [fresh, setFresh] = useState<CreatedApiKey | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<ApiKey | null>(null);
  const [creating, setCreating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function copyText(text: string, id: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId((c) => (c === id ? null : c)), 1500);
    } catch {
      setActionError("Couldn't copy to clipboard.");
    }
  }

  async function createKey() {
    setCreating(true);
    setActionError(null);
    try {
      const created = await api<CreatedApiKey>("/api/v1/keys", { method: "POST", body: {} });
      setFresh(created);
      await refresh();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setCreating(false);
    }
  }

  const configJson = meeluConfigJson({
    apiKey: fresh?.key ?? "emcp_your_key_here",
  });

  return (
    <Card className="stagger-item">
      <SectionHeader
        icon={Plug}
        title="Connect your coworker (MCP)"
        hint="Meelu's agent server speaks MCP over HTTP at http://127.0.0.1:8484/mcp/, authenticating with an x-api-key header carrying one of these keys. Drop the config below into Claude Desktop (or any MCP client) and every task starts with this site's full context."
      />
      {loading ? (
        <Spinner className="py-8" />
      ) : (
        <>
          {error && <p className="text-sm text-bad mb-3">{error}</p>}
          {actionError && <p className="text-sm text-bad mb-3">{actionError}</p>}

          <Table className="mb-3">
            <THead cols={["Name", "Key", "Last used", ""]} />
            <tbody>
              {keys.map((k) => (
                <TRow key={k.id}>
                  <TCell>{k.name}</TCell>
                  <TCell>
                    <code className="font-mono text-xs text-sub">{k.preview}</code>
                  </TCell>
                  <TCell className="text-sub whitespace-nowrap">{formatRelative(k.lastUsedAt)}</TCell>
                  <TCell className="text-right">
                    <IconButton
                      aria-label="Revoke key"
                      title={keys.length <= 1 ? "Keep at least one key" : "Revoke key"}
                      disabled={keys.length <= 1}
                      className="disabled:opacity-40 disabled:pointer-events-none hover:text-bad"
                      onClick={() => setRevoking(k)}
                    >
                      <Trash2 size={13} />
                    </IconButton>
                  </TCell>
                </TRow>
              ))}
            </tbody>
          </Table>

          <Button variant="outline" size="sm" onClick={createKey} disabled={creating}>
            <Plus size={14} /> New key
          </Button>

          {fresh && (
            <div className="mt-4 rounded-xl border border-accent/40 bg-accent/5 p-4">
              <p className="text-sm font-medium flex items-center gap-2">
                <KeyRound size={14} className="text-accent" />
                Copy {fresh.name} now
              </p>
              <p className="text-xs text-faint mt-1">
                This is the only time it is shown. The dashboard keeps a hash, not the key —
                lose it and the fix is a new key, not a lookup.
              </p>
              <div className="relative mt-3">
                <code className="block bg-panel2 rounded-lg p-3 pr-10 text-xs font-mono break-all">
                  {fresh.key}
                </code>
                <IconButton
                  aria-label="Copy key"
                  className="absolute top-2 right-2"
                  onClick={() => copyText(fresh.key, fresh.id)}
                >
                  {copiedId === fresh.id ? (
                    <Check size={14} className="text-good" />
                  ) : (
                    <Copy size={14} />
                  )}
                </IconButton>
              </div>
              <button
                className="text-xs text-faint hover:text-sub mt-3"
                onClick={() => setFresh(null)}
              >
                I&apos;ve saved it — hide
              </button>
            </div>
          )}

          <div className="relative mt-4">
            <pre className="bg-panel2 rounded-xl p-4 text-xs font-mono overflow-x-auto text-sub">
              <code>{configJson}</code>
            </pre>
            <IconButton
              aria-label="Copy MCP config"
              className="absolute top-2 right-2"
              onClick={() => copyText(configJson, "config")}
            >
              {copiedId === "config" ? <Check size={14} className="text-good" /> : <Copy size={14} />}
            </IconButton>
          </div>
          <p className="text-xs text-faint mt-2">
            The agent server runs alongside this dashboard — the URL above is its default, and
            the Meelu app follows MEELU_AGENT_MCP_URL if you move it. Google Search Console and Google Analytics connect with OAuth from the
            Connections screen in the Meelu app — the tokens stay on that device.
          </p>

          <ConfirmDelete
            open={!!revoking}
            onClose={() => setRevoking(null)}
            what={revoking ? `API key "${revoking.name}"` : "API key"}
            onConfirm={async () => {
              if (!revoking) return;
              await api(`/api/v1/keys/${revoking.id}`, { method: "DELETE" });
              await refresh();
            }}
          />
        </>
      )}
    </Card>
  );
}

function AccountSection() {
  const { data: session } = useSession();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  return (
    <Card className="stagger-item">
      <SectionHeader icon={UserRound} title="Account" />
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm text-ink">{session?.user?.name ?? "—"}</p>
          <p className="text-sm text-sub">{session?.user?.email ?? "—"}</p>
        </div>
        <Button
          variant="outline"
          className="border-bad/30 text-bad hover:bg-bad/10"
          disabled={signingOut}
          onClick={async () => {
            setSigningOut(true);
            try {
              await signOut();
              setCurrentSite(null);
              router.push("/demo/login");
            } finally {
              setSigningOut(false);
            }
          }}
        >
          <LogOut size={14} /> Sign out
        </Button>
      </div>
    </Card>
  );
}

function ModelUsageSection() {
  const usage = useSyncExternalStore(subscribeToUsage, usageSnapshot, usageServerSnapshot);

  return (
    <Card className="stagger-item">
      <SectionHeader
        icon={Cpu}
        title="Model usage"
        hint="Counted on this device against the key on the Connections page, not by this server."
      />
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs text-sub uppercase tracking-wide">This sitting</p>
        <p className="font-display text-lg text-ink tabular-nums">
          {usage ? `$${usage.costUsd.toFixed(2)}` : "—"}
        </p>
      </div>
      <p className="text-xs text-faint mt-2">
        {usage
          ? `${usage.inputTokens.toLocaleString()} in · ${usage.outputTokens.toLocaleString()} out — ` +
            `${usage.tokens.toLocaleString()} tokens over ${usage.turns} turn${usage.turns === 1 ? "" : "s"}, counted since you opened Meelu.`
          : "No turns run yet this sitting."}
      </p>
    </Card>
  );
}
