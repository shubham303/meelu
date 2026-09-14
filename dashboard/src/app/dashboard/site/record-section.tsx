"use client";

import { useEffect, useState } from "react";
import { Badge, type BadgeTone, Button, Card, Field, Input, Spinner, Textarea } from "@/components/ui";
import { GLOBAL } from "@/lib/current-site";
import { api, useApi, useCurrentSite } from "@/lib/use-api";
import { bridge, useAgentEnabled } from "@/components/agent/bridge";
import { formatRelative } from "@/lib/utils";
import type { SiteProfile, SiteSocialLink } from "@/lib/types";

const EMPTY_FORM = {
  domain: "",
  name: "",
  country: "",
  repoUrl: "",
  sitemapUrls: "",
};

type Form = typeof EMPTY_FORM;

function formOf(site: SiteProfile | null): Form {
  return {
    ...EMPTY_FORM,
    domain: site?.domain ?? "",
    name: site?.name ?? "",
    country: site?.country ?? "",
    repoUrl: site?.repoUrl ?? "",
    sitemapUrls: (site?.sitemapUrls ?? []).join("\n"),
  };
}

export function SiteRecordSection() {
  const global = useCurrentSite() === GLOBAL;
  const { data: site, loading, error, refresh } = useApi<SiteProfile | null>(
    global ? null : "/api/v1/site",
  );

  if (global) return null;

  return (
    <Card>
      <div className="mb-4">
        <h2 className="font-display text-lg text-ink">The website</h2>
        <p className="mt-1 max-w-2xl text-sm text-sub">
          What this site is, and the settings the crawl runs under. The summary is written by your
          coworker from the pages it has read; the rest you can type here or ask for in chat.
        </p>
      </div>

      {loading ? (
        <Spinner className="py-4" />
      ) : (
        <>
          {error && <p className="mb-3 text-sm text-bad">{error}</p>}
          <Details site={site ?? null} />
          {site?.domain && <CrawlToken domain={site.domain} />}
          <RecordForm
            key={site?.updatedAt ?? "new"}
            site={site ?? null}
            onSaved={refresh}
          />
        </>
      )}
    </Card>
  );
}

function Details({ site }: { site: SiteProfile | null }) {
  if (!site) return null;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Badge tone={site.summary ? "good" : "warn"}>
          {site.summary ? "Described" : "Not described yet"}
        </Badge>
        <span className="text-xs text-faint">
          {site.lastCrawledAt
            ? `Crawled ${formatRelative(site.lastCrawledAt)}`
            : "Never crawled"}
          {site.sitemapUrlCount ? ` · ${site.sitemapUrlCount} URLs in the sitemap` : ""}
        </span>
      </div>

      {site.summary ? (
        <p className="max-w-2xl text-sm leading-relaxed text-sub">{site.summary}</p>
      ) : (
        <p className="text-sm text-faint">
          Crawl the site, then ask your coworker to write up what it is.
        </p>
      )}
    </div>
  );
}

function SocialLinks({ links }: { links: SiteSocialLink[] }) {
  if (links.length === 0) {
    return (
      <p className="text-sm text-faint">
        None found yet — a crawl picks these up from the pages it reads.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {links.map((link) => (
        <a key={link.url} href={link.url} target="_blank" rel="noreferrer">
          <Badge className="hover:border-accent/40 hover:text-accent">
            {link.platform}
            {link.handle ? ` · ${link.handle}` : ""}
          </Badge>
        </a>
      ))}
    </div>
  );
}

function originOf(domain: string): string | null {
  const trimmed = domain.trim();
  if (!trimmed) return null;
  try {
    return new URL(trimmed.startsWith("http") ? trimmed : `https://${trimmed}`).origin;
  } catch {
    return null;
  }
}

function served(status: number | null | undefined): { tone: BadgeTone; label: string } {
  if (status === undefined || status === null) return { tone: "neutral", label: "not looked for yet" };
  if (status === 200) return { tone: "good", label: "served" };
  if (status === 404 || status === 410) return { tone: "warn", label: "not there" };
  return { tone: "bad", label: `HTTP ${status}` };
}

function SiteFiles({ domain, site }: { domain: string; site: SiteProfile | null }) {
  const origin = originOf(domain);
  if (!origin) return null;

  const files = [
    { path: "/robots.txt", status: site?.robotsStatus },
    { path: "/llms.txt", status: site?.llmsStatus },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {files.map(({ path, status }) => {
        const { tone, label } = served(status);
        return (
          <a key={path} href={`${origin}${path}`} target="_blank" rel="noreferrer">
            <Badge tone={tone} className="hover:border-accent/40">
              {origin}
              {path} · {label}
            </Badge>
          </a>
        );
      })}
    </div>
  );
}

function CrawlToken({ domain }: { domain: string }) {
  const inApp = useAgentEnabled();
  const [token, setToken] = useState<string | null>(null);
  const [shown, setShown] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!inApp) return;
    let live = true;
    void bridge()
      ?.crawlToken?.(domain)
      .then((res) => {
        if (live) setToken(res?.token ?? null);
      });
    return () => {
      live = false;
    };
  }, [inApp, domain]);

  if (!inApp || !token) return null;

  return (
    <div className="mt-5 border-t border-edge pt-5">
      <h3 className="text-sm font-medium text-ink">Crawl access token</h3>
      <p className="mt-1 max-w-2xl text-sm text-sub">
        The crawl reads your site from this machine, so a firewall or bot protection will treat
        it as a bot. This token is made here and never leaves the machine. Every request carries
        it as{" "}
        <code className="font-mono text-accent">X-Meelu-Crawl</code> — allow that header and the
        crawl gets through.{" "}
        <a href="/docs/crawl-access" target="_blank" rel="noreferrer" className="text-accent hover:underline">
          How to set the rule
        </a>
      </p>
      <div className="mt-3 flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-lg border border-edge bg-panel2 px-3 py-2 font-mono text-xs text-sub">
          {shown ? token : "•".repeat(token.length)}
        </code>
        <Button variant="outline" onClick={() => setShown((s) => !s)}>
          {shown ? "Hide" : "Reveal"}
        </Button>
        <Button
          variant="outline"
          onClick={async () => {
            await navigator.clipboard.writeText(token);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
    </div>
  );
}

function RecordForm({ site, onSaved }: { site: SiteProfile | null; onSaved: () => Promise<void> }) {
  const saved = formOf(site);
  const [form, setForm] = useState<Form>(saved);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const dirty = (Object.keys(saved) as (keyof Form)[]).some((k) => form[k] !== saved[k]);

  const set = (field: keyof Form) => (value: string) => {
    setStatus(null);
    setForm((f) => ({ ...f, [field]: value }));
  };

  async function save() {
    setSaving(true);
    setStatus(null);
    try {
      await api("/api/v1/site", {
        method: "PUT",
        body: {
          domain: form.domain.trim(),
          name: form.name.trim(),
          country: form.country.trim(),
          repoUrl: form.repoUrl.trim(),
          sitemapUrls: form.sitemapUrls
            .split("\n")
            .map((u) => u.trim())
            .filter(Boolean),
        },
      });
      await onSaved();
      setStatus("Saved.");
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-5 border-t border-edge pt-5">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Website" hint="The host it serves on, www and all">
          <Input
            value={form.domain}
            onChange={(e) => set("domain")(e.target.value)}
            placeholder="www.yourproduct.com"
          />
        </Field>
        <Field label="Business name">
          <Input
            value={form.name}
            onChange={(e) => set("name")(e.target.value)}
            placeholder="e.g. Ledgerly"
          />
        </Field>
        <Field label="Country">
          <Input
            value={form.country}
            onChange={(e) => set("country")(e.target.value)}
            placeholder="US"
          />
        </Field>
        <div className="sm:col-span-2">
          <Field
            label="Sitemaps"
            hint="One URL per line. The crawl reads the pages a sitemap lists and nothing else, so it needs one; leave this blank and it looks in the usual places itself."
          >
            <Textarea
              rows={3}
              value={form.sitemapUrls}
              onChange={(e) => set("sitemapUrls")(e.target.value)}
              placeholder="https://example.com/sitemap.xml"
            />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field
            label="Site files"
            hint="The well-known locations on this domain — robots.txt says what a crawler may read, llms.txt says what a model should. Nothing to type here; open either to see what your site serves."
          >
            <SiteFiles domain={form.domain} site={site} />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field
            label="Code repository"
            hint="Where this website's project lives, so a fix can point at the template behind a problem rather than every page that shows it — read through your own GitHub tools, never a token we hold."
          >
            <Input
              value={form.repoUrl}
              onChange={(e) => set("repoUrl")(e.target.value)}
              placeholder="https://github.com/you/your-site"
            />
          </Field>
        </div>
        <div className="sm:col-span-2">
          <Field
            label="Social profiles"
            hint="Found by the crawl and written up by your coworker, so there is nothing to type here — ask in chat to correct one."
          >
            <SocialLinks links={site?.socialLinks ?? []} />
          </Field>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <Button onClick={save} disabled={saving || !dirty}>
          {saving ? "Saving…" : "Save"}
        </Button>
        {status && (
          <p className={status === "Saved." ? "text-sm text-sub" : "text-sm text-bad"}>{status}</p>
        )}
      </div>
    </div>
  );
}
