"use client";

import { useState } from "react";
import { Download, Loader2, RefreshCw } from "lucide-react";
import { Button, Card } from "@/components/ui";

interface AppUpdate {
  currentVersion: string;
  version: string;
  downloadUrl: string;
}

interface CheckResult {
  currentVersion?: string;
  update?: AppUpdate | null;
  error?: string;
}

interface UpdateBridge {
  checkUpdate?: () => Promise<CheckResult>;
  downloadUpdate?: () => Promise<{ ok?: boolean }>;
}

function updateBridge(): UpdateBridge | null {
  if (typeof window === "undefined") return null;
  return (window as Window & { meeluAgent?: UpdateBridge }).meeluAgent ?? null;
}

export function AppUpdateCard() {
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<CheckResult | null>(null);

  const check = async () => {
    const checkUpdate = updateBridge()?.checkUpdate;
    if (!checkUpdate) {
      setResult({
        error: "This version of Meelu cannot check on demand. Get the latest from meelu.tech/download.",
      });
      return;
    }
    setChecking(true);
    try {
      setResult(await checkUpdate());
    } catch {
      setResult({ error: "The update check failed. Try again." });
    } finally {
      setChecking(false);
    }
  };

  const update = result?.update ?? null;

  return (
    <Card className="stagger-item">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-2 min-w-0">
          <RefreshCw size={15} className="text-accent shrink-0 mt-0.5" />
          <div className="min-w-0">
            <div className="font-medium">App updates</div>
            <p className="text-sm text-sub mt-0.5">
              {result?.error
                ? result.error
                : update
                  ? `Meelu ${update.version} is available · you have ${update.currentVersion}. Download it, quit Meelu, then install it over this one. Your sign-in and settings stay.`
                  : result
                    ? `You have the latest version${result.currentVersion ? ` (${result.currentVersion})` : ""}.`
                    : "Meelu checks for a new version every 10 minutes. Check now to see it straight away."}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {update && (
            <Button size="sm" onClick={() => void updateBridge()?.downloadUpdate?.()}>
              <Download size={13} />
              Download {update.version}
            </Button>
          )}
          <Button size="sm" variant="outline" disabled={checking} onClick={() => void check()}>
            {checking && <Loader2 size={13} className="animate-spin" />}
            {checking ? "Checking…" : "Check for updates"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
