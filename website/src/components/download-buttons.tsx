"use client";

import Link from "next/link";
import { useSyncExternalStore, type ReactNode } from "react";
import { Download } from "lucide-react";
import { useDownloadPrompt } from "@/components/download-prompt";

type Platform = "mac" | "windows" | "other";

type Build = {
  id: string;
  platform: Exclude<Platform, "other">;
  label: string;
  detail: string;
  href: string;
};

const DOWNLOADS = "https://downloads.meelu.tech";

const builds: Build[] = [
  {
    id: "mac-arm64",
    href: `${DOWNLOADS}/Meelu-mac-arm64.dmg`,
    platform: "mac",
    label: "Download for macOS",
    detail: "Apple Silicon (M1–M4)",
  },
  {
    id: "mac-x64",
    href: `${DOWNLOADS}/Meelu-mac-x64.dmg`,
    platform: "mac",
    label: "Download for macOS",
    detail: "Intel",
  },
  {
    id: "windows-x64",
    href: `${DOWNLOADS}/Meelu-windows-x64.exe`,
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

function BetaTag() {
  return (
    <span className="rounded-full bg-white/20 px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest">
      Beta
    </span>
  );
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

export function HeroDownload({
  children,
  align = "center",
}: {
  children?: ReactNode;
  align?: "center" | "start";
}) {
  const platform = usePlatform();
  const primary = builds.find((build) => build.platform === platform);
  const { onDownloadClick, prompt } = useDownloadPrompt();
  const alignment = align === "start" ? "items-start" : "items-center";

  return (
    <div className={`flex flex-col ${alignment}`}>
      {prompt}
      <div className={`flex flex-col justify-center gap-3 sm:flex-row ${alignment}`}>
        <a
          href={primary?.href ?? "/download"}
          onClick={primary ? onDownloadClick(primary) : undefined}
          className="inline-flex h-12 items-center gap-2.5 rounded-lg bg-accent px-6 text-base font-medium text-white transition-colors hover:bg-accent-hi"
        >
          <Download size={18} />
          {primary?.label ?? "Download the app"}
          <BetaTag />
        </a>
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
      <p className="mt-2 max-w-md text-xs text-faint text-pretty">Meelu is in beta.</p>
    </div>
  );
}

export function DownloadButtons() {
  const platform = usePlatform();
  const primary = builds.find((build) => build.platform === platform);
  const rest = builds.filter((build) => build !== primary);
  const { onDownloadClick, prompt } = useDownloadPrompt();

  return (
    <div className="flex w-full flex-col items-center">
      {prompt}
      {primary && (
        <>
          <a
            href={primary.href}
            onClick={onDownloadClick(primary)}
            className="inline-flex h-12 items-center gap-2.5 rounded-lg bg-accent px-6 text-base font-medium text-white transition-colors hover:bg-accent-hi"
          >
            <Download size={18} />
            {primary.label}
            <BetaTag />
          </a>
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
            <a
              key={build.id}
              href={build.href}
              onClick={onDownloadClick(build)}
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
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
