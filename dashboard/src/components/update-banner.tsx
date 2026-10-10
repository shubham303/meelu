"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";
import { Button } from "@/components/ui";

interface AppUpdate {
  currentVersion: string;
  version: string;
  downloadUrl: string;
}

interface UpdateBridge {
  appUpdate?: () => Promise<{ update?: AppUpdate | null }>;
  downloadUpdate?: () => Promise<{ ok?: boolean }>;
  onAppUpdate?: (cb: (update: AppUpdate) => void) => () => void;
}

const DISMISSED_KEY = "meelu.update.dismissed";

function updateBridge(): UpdateBridge | null {
  if (typeof window === "undefined") return null;
  return (window as Window & { meeluAgent?: UpdateBridge }).meeluAgent ?? null;
}

function dismissedVersion(): string | null {
  try {
    return localStorage.getItem(DISMISSED_KEY);
  } catch {
    return null;
  }
}

function rememberDismissed(version: string) {
  try {
    localStorage.setItem(DISMISSED_KEY, version);
  } catch {}
}

export function UpdateBanner() {
  const [update, setUpdate] = useState<AppUpdate | null>(null);

  useEffect(() => {
    const bridge = updateBridge();
    if (!bridge?.appUpdate) return;
    const offer = (next: AppUpdate | null | undefined) => {
      if (next && next.version !== dismissedVersion()) setUpdate(next);
    };
    void bridge.appUpdate().then((res) => offer(res?.update)).catch(() => {});
    return bridge.onAppUpdate?.(offer);
  }, []);

  if (!update) return null;

  const dismiss = () => {
    rememberDismissed(update.version);
    setUpdate(null);
  };

  return (
    <div role="status" className="border-b border-accent/30 bg-accent/10 px-8 py-3 text-sm text-ink">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-4 gap-y-2">
        <Download size={15} className="shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <span className="font-medium">Meelu {update.version} is available</span>
          <span className="text-sub">
            {" "}· you have {update.currentVersion}. Download it, quit Meelu, then install it over this one. Your sign-in and settings stay.
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button size="sm" onClick={() => void updateBridge()?.downloadUpdate?.()}>
            Download
          </Button>
          <Button size="sm" variant="ghost" onClick={dismiss} aria-label="Dismiss">
            <X size={13} />
          </Button>
        </div>
      </div>
    </div>
  );
}
