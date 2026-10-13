"use client";

import { useEffect, useMemo, useRef, useState, type FormEvent, type MouseEvent } from "react";
import { Download, X } from "lucide-react";
import { COUNTRY_CODES } from "@/lib/downloads/countries";

export type PromptedBuild = { id: string; href: string; label: string; detail: string };

const SUBMITTED_KEY = "meelu-download-details";

function alreadySubmitted(): boolean {
  try {
    return window.localStorage.getItem(SUBMITTED_KEY) === "1";
  } catch {
    return false;
  }
}

function rememberSubmitted() {
  try {
    window.localStorage.setItem(SUBMITTED_KEY, "1");
  } catch {}
}

function startDownload(href: string) {
  window.location.href = href;
}

function localeCountry(): string {
  for (const tag of navigator.languages ?? [navigator.language]) {
    try {
      const region = new Intl.Locale(tag).maximize().region;
      if (region && (COUNTRY_CODES as readonly string[]).includes(region)) return region;
    } catch {}
  }
  return "";
}

export function useDownloadPrompt() {
  const [pending, setPending] = useState<PromptedBuild | null>(null);

  function onDownloadClick(build: PromptedBuild) {
    return (event: MouseEvent<HTMLAnchorElement>) => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      if (alreadySubmitted()) return;
      event.preventDefault();
      setPending(build);
    };
  }

  const prompt = pending ? (
    <DownloadPrompt key={pending.id} build={pending} onClose={() => setPending(null)} />
  ) : null;

  return { onDownloadClick, prompt };
}

function DownloadPrompt({ build, onClose }: { build: PromptedBuild; onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState(localeCountry);
  const [company, setCompany] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const countries = useMemo(() => {
    const names = new Intl.DisplayNames(undefined, { type: "region" });
    return COUNTRY_CODES.map((code) => ({ code, name: names.of(code) ?? code })).sort((a, b) =>
      a.name.localeCompare(b.name),
    );
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
  }, []);

  function finish() {
    startDownload(build.href);
    onClose();
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSending(true);
    setError(null);
    try {
      const response = await fetch("/api/downloads", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, country, build: build.id, company }),
      });
      if (response.status === 400) {
        const data = (await response.json().catch(() => ({}))) as { message?: string };
        setError(data.message ?? "Check your details and try again.");
        setSending(false);
        return;
      }
      if (response.ok) rememberSubmitted();
    } catch {}
    finish();
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-edge bg-panel p-0 text-left text-ink shadow-xl backdrop:bg-black/50"
    >
      <div className="relative p-6">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 rounded-md p-1 text-faint transition-colors hover:text-ink"
        >
          <X size={18} />
        </button>

        <div className="pr-6">
          <h2 className="font-display text-xl tracking-tight text-ink">Before you download</h2>
          <p className="mt-2 text-sm text-sub text-pretty">
            Tell us who you are so we can let you know about fixes and new versions during the
            beta. This is optional.
          </p>
          <p className="mt-1 text-xs text-faint">
            {build.label} · {build.detail}
          </p>
        </div>

        <form onSubmit={submit} className="mt-6 flex flex-col gap-3">
          <label htmlFor="download-email" className="text-xs font-medium text-sub">
            Email
          </label>
          <input
            id="download-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@company.com"
            className="h-11 w-full rounded-lg border border-edge bg-transparent px-3 text-base text-ink outline-none transition-colors placeholder:text-faint focus:border-accent sm:text-sm"
          />
          <label htmlFor="download-country" className="mt-1 text-xs font-medium text-sub">
            Country
          </label>
          <select
            id="download-country"
            required
            autoComplete="country"
            value={country}
            onChange={(event) => setCountry(event.target.value)}
            className="h-11 w-full rounded-lg border border-edge bg-panel px-3 text-base text-ink outline-none transition-colors focus:border-accent sm:text-sm"
          >
            <option value="" disabled>
              Choose your country
            </option>
            {countries.map((entry) => (
              <option key={entry.code} value={entry.code}>
                {entry.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            name="company"
            tabIndex={-1}
            autoComplete="off"
            aria-hidden
            value={company}
            onChange={(event) => setCompany(event.target.value)}
            className="hidden"
          />
          {error && <p className="text-sm text-warn">{error}</p>}
          <div className="mt-2 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={finish}
              className="inline-flex h-11 items-center justify-center rounded-lg border border-edge px-5 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              Skip and download
            </button>
            <button
              type="submit"
              disabled={sending}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
            >
              <Download size={16} />
              {sending ? "Starting…" : "Download"}
            </button>
          </div>
        </form>
      </div>
    </dialog>
  );
}
