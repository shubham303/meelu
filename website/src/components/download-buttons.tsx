"use client";

import Link from "next/link";
import { useState, useSyncExternalStore, type ReactNode } from "react";
import { Download } from "lucide-react";
import { WaitlistDialog } from "@/components/waitlist-dialog";

type Platform = "mac" | "windows" | "other";

type Build = {
  id: string;
  platform: Exclude<Platform, "other">;
  label: string;
  detail: string;
};

const builds: Build[] = [
  {
    id: "mac-arm64",
    platform: "mac",
    label: "Download for macOS",
    detail: "Apple Silicon (M1–M4)",
  },
  {
    id: "mac-x64",
    platform: "mac",
    label: "Download for macOS",
    detail: "Intel",
  },
  {
    id: "windows-x64",
    platform: "windows",
    label: "Download for Windows",
    detail: "Windows 10/11 (64-bit)",
  },
];

type NavigatorWithUAData = Navigator & {
  userAgentData?: { platform?: string };
};

function detectPlatform(): Platform {
  const nav = navigator as NavigatorWithUAData;
  const ua = nav.userAgent;
  if (/iPhone|iPad|iPod|Android/i.test(ua)) return "other";
  const hint = (nav.userAgentData?.platform || ua).toLowerCase();
  if (hint.includes("mac")) return "mac";
  if (hint.includes("win")) return "windows";
  return "other";
}

function subscribe() {
  return () => {};
}

function serverPlatform(): Platform {
  return "other";
}

function usePlatform(): Platform {
  return useSyncExternalStore(subscribe, detectPlatform, serverPlatform);
}

function useWaitlist() {
  const [requested, setRequested] = useState<Platform | null>(null);
  const dialog = (
    <WaitlistDialog
      open={requested !== null}
      platform={requested ?? "other"}
      onClose={() => setRequested(null)}
    />
  );
  return { request: setRequested, dialog };
}

export function HeroDownload({ children }: { children?: ReactNode }) {
  const platform = usePlatform();
  const primary = builds.find((build) => build.platform === platform);
  const waitlist = useWaitlist();

  return (
    <div className="flex flex-col items-center">
      <div className="flex flex-col items-center justify-center gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => waitlist.request(platform)}
          className="inline-flex h-12 items-center gap-2.5 rounded-lg bg-accent px-6 text-base font-medium text-white transition-colors hover:bg-accent-hi"
        >
          <Download size={18} />
          {primary?.label ?? "Download the app"}
        </button>
        {children}
      </div>
      <p className="mt-3 text-xs text-faint">
        {primary ? `${primary.detail} · ` : "For macOS and Windows · "}
        <Link
          href="/download"
          className="text-sub underline decoration-edge underline-offset-4 transition-colors hover:text-ink hover:decoration-accent"
        >
          {primary ? "Other platforms" : "All downloads"}
        </Link>
      </p>
      {waitlist.dialog}
    </div>
  );
}

export function DownloadButtons() {
  const platform = usePlatform();
  const primary = builds.find((build) => build.platform === platform);
  const waitlist = useWaitlist();
  const rest = builds.filter((build) => build !== primary);

  return (
    <div className="flex w-full flex-col items-center">
      {primary && (
        <>
          <button
            type="button"
            onClick={() => waitlist.request(primary.platform)}
            className="inline-flex h-12 items-center gap-2.5 rounded-lg bg-accent px-6 text-base font-medium text-white transition-colors hover:bg-accent-hi"
          >
            <Download size={18} />
            {primary.label}
          </button>
          <p className="mt-2.5 text-xs text-faint">{primary.detail}</p>
        </>
      )}

      <div className={`${primary ? "mt-10" : ""} w-full max-w-xl`}>
        {primary && (
          <p className="text-center font-mono text-[11px] uppercase tracking-widest text-faint">
            Other downloads
          </p>
        )}
        <div className="mt-3 divide-y divide-edge rounded-2xl border border-edge bg-panel">
          {rest.map((build) => (
            <button
              type="button"
              key={build.id}
              onClick={() => waitlist.request(build.platform)}
              className="group flex w-full items-center justify-between gap-4 px-5 py-4 transition-colors first:rounded-t-2xl last:rounded-b-2xl hover:bg-panel2"
            >
              <span className="flex flex-col text-left">
                <span className="text-sm font-medium text-ink">{build.label}</span>
                <span className="text-xs text-sub">{build.detail}</span>
              </span>
              <Download
                size={16}
                className="shrink-0 text-faint transition-colors group-hover:text-accent"
              />
            </button>
          ))}
        </div>
      </div>
      {waitlist.dialog}
    </div>
  );
}
