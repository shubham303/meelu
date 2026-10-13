"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { CreditCard, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui";
import { api, useCurrentSite } from "@/lib/use-api";
import { formatUsd } from "@/lib/utils";
import {
  billingBlock,
  clearBillingBlock,
  resolveBillingBlock,
  subscribeToBillingBlock,
  type BillingBlock,
} from "@/lib/billing-block";

const POLL_MS = 10_000;

interface Balance {
  balanceUsd: number;
}

interface SiteBilling {
  status: string;
  nextChargeAt: string | null;
}

function usd(value: number | undefined): string | null {
  return value === undefined ? null : formatUsd(value);
}

async function resolved(block: BillingBlock): Promise<boolean> {
  if (block.code === "site_disabled" && block.siteId) {
    const state = await api<SiteBilling>(`/api/v1/credits/sites/${block.siteId}`);
    return state.status === "active";
  }
  const balance = await api<Balance>("/api/v1/credits");
  return balance.balanceUsd >= (block.minimumUsd ?? 0.2);
}

export function BillingBanner() {
  const block = useSyncExternalStore(subscribeToBillingBlock, billingBlock, () => null);
  const [checking, setChecking] = useState(false);

  const check = useCallback(async () => {
    if (!block) return;
    setChecking(true);
    try {
      if (await resolved(block)) resolveBillingBlock();
    } catch {
      // leave the banner up; the next check decides
    } finally {
      setChecking(false);
    }
  }, [block]);

  const siteId = useCurrentSite();
  useEffect(() => {
    if (block?.code === "site_disabled" && block.siteId && block.siteId !== siteId) {
      clearBillingBlock("site_disabled");
    }
  }, [block, siteId]);

  useEffect(() => {
    if (!block) return;
    const timer = setInterval(() => void check(), POLL_MS);
    return () => clearInterval(timer);
  }, [block, check]);

  if (!block) return null;

  const balance = usd(block.balanceUsd);

  return (
    <div
      role="status"
      className="border-b border-warn/30 bg-warn/10 px-8 py-3 text-sm text-ink"
    >
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-4 gap-y-2">
        <CreditCard size={15} className="shrink-0 text-warn" />
        <div className="min-w-0 flex-1">
          <span className="font-medium">
            {block.code === "site_disabled"
              ? "This website is paused"
              : "Not enough credits"}
          </span>
          <span className="text-sub"> · {block.message}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {balance && <span className="text-sub tabular-nums">Balance {balance}</span>}
          <Button size="sm" variant="ghost" onClick={() => void check()} disabled={checking}>
            <RefreshCw size={13} className={checking ? "animate-spin" : undefined} />
            Check again
          </Button>
          <Link href="/dashboard/credits">
            <Button size="sm">Add credits</Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
