"use client";

import { Coins } from "lucide-react";
import { Card } from "@/components/ui";
import { cn } from "@/lib/utils";
import { usePagedApi, useApi } from "@/lib/use-api";
import { formatRelative, formatUsd } from "@/lib/utils";

interface Balance {
  balanceMicros: number;
  balanceUsd: number;
}

interface LedgerEntry {
  id: string;
  kind: string;
  deltaUsd: number;
  balanceAfterUsd: number;
  note: string | null;
  createdAt: string;
}

export function CreditsCard() {
  const { data: balance } = useApi<Balance>("/api/v1/credits");
  const { data: ledger } = usePagedApi<LedgerEntry>("/api/v1/credits/ledger?page_size=5");
  const entries = ledger?.data ?? [];

  return (
    <Card className="stagger-item">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2 min-w-0">
          <Coins size={15} className="text-accent shrink-0 mt-0.5" />
          <div className="min-w-0">
            <div className="font-medium">Meelu credits</div>
            <p className="text-sm text-sub mt-0.5">
              Search data and social listening run through Meelu&apos;s own
              vendor accounts. Each vendor call is charged to this balance at cost; results
              already in Meelu&apos;s database are free.
            </p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xl font-semibold tabular-nums">
            {balance ? formatUsd(balance.balanceUsd) : "—"}
          </div>
          <div className="text-xs text-sub">available</div>
        </div>
      </div>
      {entries.length > 0 && (
        <ul className="mt-4 divide-y divide-edge text-sm">
          {entries.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-3 py-1.5">
              <span className="truncate text-sub">
                <span className="text-ink">{e.kind}</span>
                {e.note ? ` · ${e.note}` : ""}
              </span>
              <span className="tabular-nums shrink-0">
                <span className={e.deltaUsd < 0 ? "text-bad" : "text-good"}>
                  {e.deltaUsd < 0 ? "−" : "+"}
                  {formatUsd(Math.abs(e.deltaUsd))}
                </span>
                <span className="text-sub ml-2 text-xs">{formatRelative(e.createdAt)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
