"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Coins, ExternalLink, Loader2 } from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import {
  Badge,
  Button,
  Card,
  IconButton,
  Input,
  PageHeader,
  Spinner,
  Table,
  Tabs,
  TCell,
  THead,
  TRow,
} from "@demo/components/ui";
import { api, usePagedApi } from "@demo/lib/use-api";
import { useCredits } from "@demo/lib/use-credits";
import { formatDate, formatRelative, formatUsd } from "@demo/lib/utils";

const PRESETS = [5, 10, 20, 50];
const MIN_TOPUP_USD = 5;
const MAX_TOPUP_USD = 500;
const PAGE_SIZE = 20;
const CONFIRM_POLL_MS = 4_000;

interface Payment {
  id: string;
  status: "pending" | "succeeded" | "failed" | "cancelled";
  creditUsd: number;
  checkoutUrl: string | null;
  paidAmount: number | null;
  paidCurrency: string | null;
  creditedAt: string | null;
  createdAt: string;
}

interface CheckoutResponse {
  paymentId: string;
  checkoutUrl: string;
}

interface LedgerEntry {
  id: string;
  kind: string;
  deltaUsd: number;
  balanceAfterUsd: number;
  note: string | null;
  createdAt: string;
}

const STATUS_TONE = {
  pending: "warn",
  succeeded: "good",
  failed: "bad",
  cancelled: "neutral",
} as const;

const KIND_LABEL: Record<string, string> = {
  purchase: "Top-up",
  grant: "Free credits",
  usage: "Usage",
  site_day: "Website",
};

export default function CreditsPage() {
  const balance = useCredits();
  const [tab, setTab] = useState<"payments" | "activity">("payments");
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [ledgerPage, setLedgerPage] = useState(1);
  const payments = usePagedApi<Payment>(`/api/v1/payments?page=${paymentsPage}&page_size=${PAGE_SIZE}`);
  const ledger = usePagedApi<LedgerEntry>(`/api/v1/credits/ledger?page=${ledgerPage}&page_size=${PAGE_SIZE}`);

  const refreshBalance = balance.refresh;
  const refreshPayments = payments.refresh;
  const refreshLedger = ledger.refresh;
  const settled = useCallback(async () => {
    await Promise.all([refreshBalance(), refreshPayments(), refreshLedger()]);
  }, [refreshBalance, refreshPayments, refreshLedger]);

  return (
    <PageEnter>
      <PageHeader
        title="Credits"
        description="Search data, AI model calls and websites are charged to this balance at cost. Results already in Meelu's database are free."
      />
      <Stagger className="space-y-5">
        <TopUpCard balanceUsd={balance.data?.balanceUsd} onSettled={settled} />
        <div className="stagger-item">
          <Tabs
            tabs={[
              { key: "payments", label: "Payments" },
              { key: "activity", label: "Activity" },
            ]}
            active={tab}
            onChange={(k) => setTab(k as "payments" | "activity")}
          />
          {tab === "payments" ? (
            <PaymentsTable
              loading={payments.loading}
              rows={payments.data?.data ?? []}
              page={paymentsPage}
              totalPages={payments.data?.pagination.total_pages ?? 1}
              onPage={setPaymentsPage}
            />
          ) : (
            <LedgerTable
              loading={ledger.loading}
              rows={ledger.data?.data ?? []}
              page={ledgerPage}
              totalPages={ledger.data?.pagination.total_pages ?? 1}
              onPage={setLedgerPage}
            />
          )}
        </div>
      </Stagger>
    </PageEnter>
  );
}

function TopUpCard({
  balanceUsd,
  onSettled,
}: {
  balanceUsd: number | undefined;
  onSettled: () => Promise<void>;
}) {
  const [starting, setStarting] = useState<number | "custom" | null>(null);
  const [custom, setCustom] = useState("");
  const [waiting, setWaiting] = useState<CheckoutResponse | null>(null);
  const [notice, setNotice] = useState<{ tone: "good" | "bad"; text: string } | null>(null);

  useEffect(() => {
    if (!waiting) return;
    const timer = setInterval(async () => {
      try {
        const payment = await api<Payment>(`/api/v1/payments/${waiting.paymentId}`);
        if (payment.status === "pending") return;
        setWaiting(null);
        setNotice(
          payment.status === "succeeded"
            ? { tone: "good", text: `${formatUsd(payment.creditUsd)} added to your balance.` }
            : { tone: "bad", text: `The payment was ${payment.status}. Nothing was charged to your credits.` },
        );
        await onSettled();
      } catch {}
    }, CONFIRM_POLL_MS);
    return () => clearInterval(timer);
  }, [waiting, onSettled]);

  const customUsd = Number(custom);
  const customValid =
    custom.trim() !== "" && Number.isFinite(customUsd) && customUsd >= MIN_TOPUP_USD && customUsd <= MAX_TOPUP_USD;

  async function buy(amountUsd: number, key: number | "custom" = amountUsd) {
    setStarting(key);
    setNotice(null);
    try {
      const checkout = await api<CheckoutResponse>("/api/v1/payments/checkout", {
        method: "POST",
        body: { amountUsd },
      });
      window.open(checkout.checkoutUrl, "_blank", "noopener");
      setWaiting(checkout);
      await onSettled();
    } catch (e) {
      setNotice({ tone: "bad", text: e instanceof Error ? e.message : "Could not start the checkout." });
    } finally {
      setStarting(null);
    }
  }

  return (
    <Card className="stagger-item">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-accent-soft p-2.5">
            <Coins size={18} className="text-accent" />
          </div>
          <div>
            <p className="text-xs text-sub uppercase tracking-wide">Balance</p>
            <p className="font-display text-3xl text-ink tabular-nums mt-0.5">
              {balanceUsd === undefined ? "—" : `$${balanceUsd.toFixed(2)}`}
            </p>
          </div>
        </div>
        <div>
          <p className="text-xs text-sub uppercase tracking-wide mb-2">Add credits</p>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((amount) => (
              <Button
                key={amount}
                variant={amount === 20 ? "primary" : "outline"}
                disabled={starting !== null || waiting !== null}
                onClick={() => void buy(amount)}
              >
                {starting === amount && <Loader2 size={14} className="animate-spin" />}${amount}
              </Button>
            ))}
          </div>
          <form
            className="mt-2 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (customValid) void buy(Math.round(customUsd * 100) / 100, "custom");
            }}
          >
            <div className="relative w-36">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-sub">$</span>
              <Input
                type="number"
                inputMode="decimal"
                min={MIN_TOPUP_USD}
                max={MAX_TOPUP_USD}
                step="0.01"
                value={custom}
                onChange={(e) => setCustom(e.target.value)}
                placeholder="Other amount"
                aria-label="Other amount in USD"
                className="w-36 pl-6"
              />
            </div>
            <Button type="submit" variant="outline" disabled={!customValid || starting !== null || waiting !== null}>
              {starting === "custom" && <Loader2 size={14} className="animate-spin" />}
              Add
            </Button>
          </form>
          {custom.trim() !== "" && !customValid && (
            <p className="text-xs text-bad mt-1.5">
              Enter an amount from ${MIN_TOPUP_USD} to ${MAX_TOPUP_USD}.
            </p>
          )}
          <p className="text-xs text-faint mt-2 max-w-xs">
            $1 buys $1 of credits. Sales tax or VAT for your country is added at checkout.
          </p>
        </div>
      </div>

      {waiting && (
        <div className="mt-5 flex flex-wrap items-center gap-3 rounded-xl border border-accent/30 bg-accent-soft px-4 py-3 text-sm">
          <Loader2 size={15} className="animate-spin text-accent shrink-0" />
          <span className="flex-1 min-w-0 text-ink">
            Finish paying in your browser. Your balance updates here once the payment clears.
          </span>
          <Button size="sm" variant="ghost" onClick={() => window.open(waiting.checkoutUrl, "_blank", "noopener")}>
            <ExternalLink size={13} /> Open checkout
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setWaiting(null)}>
            Stop waiting
          </Button>
        </div>
      )}
      {notice && (
        <p className={`mt-4 text-sm ${notice.tone === "good" ? "text-good" : "text-bad"}`}>{notice.text}</p>
      )}
    </Card>
  );
}

function Pager({ page, totalPages, onPage }: { page: number; totalPages: number; onPage: (p: number) => void }) {
  if (totalPages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 mt-3 text-xs text-sub">
      <IconButton aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        <ChevronLeft size={14} />
      </IconButton>
      <span className="tabular-nums">
        {page} / {totalPages}
      </span>
      <IconButton aria-label="Next page" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
        <ChevronRight size={14} />
      </IconButton>
    </div>
  );
}

function paid(p: Payment): string {
  if (p.paidAmount == null) return "—";
  return `${(p.paidAmount / 100).toFixed(2)} ${p.paidCurrency ?? ""}`.trim();
}

function PaymentsTable({
  loading,
  rows,
  page,
  totalPages,
  onPage,
}: {
  loading: boolean;
  rows: Payment[];
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}) {
  if (loading) return <Spinner className="py-10" />;
  if (rows.length === 0) return <p className="text-sm text-sub py-6">No payments yet.</p>;
  return (
    <>
      <Table>
        <THead cols={["Date", "Credits", "Paid", "Status"]} />
        <tbody>
          {rows.map((p) => (
            <TRow key={p.id}>
              <TCell className="text-sub whitespace-nowrap">{formatDate(p.createdAt)}</TCell>
              <TCell className="tabular-nums">{formatUsd(p.creditUsd)}</TCell>
              <TCell className="tabular-nums text-sub">{paid(p)}</TCell>
              <TCell>
                <Badge tone={STATUS_TONE[p.status]}>{p.status}</Badge>
              </TCell>
            </TRow>
          ))}
        </tbody>
      </Table>
      <Pager page={page} totalPages={totalPages} onPage={onPage} />
    </>
  );
}

function LedgerTable({
  loading,
  rows,
  page,
  totalPages,
  onPage,
}: {
  loading: boolean;
  rows: LedgerEntry[];
  page: number;
  totalPages: number;
  onPage: (p: number) => void;
}) {
  if (loading) return <Spinner className="py-10" />;
  if (rows.length === 0) return <p className="text-sm text-sub py-6">No activity yet.</p>;
  return (
    <>
      <Table>
        <THead cols={["When", "What", "Amount", "Balance"]} />
        <tbody>
          {rows.map((e) => (
            <TRow key={e.id}>
              <TCell className="text-sub whitespace-nowrap">{formatRelative(e.createdAt)}</TCell>
              <TCell className="min-w-0">
                <span className="text-ink">{KIND_LABEL[e.kind] ?? e.kind}</span>
                {e.note && <span className="text-sub"> · {e.note}</span>}
              </TCell>
              <TCell className={`tabular-nums whitespace-nowrap ${e.deltaUsd < 0 ? "text-bad" : "text-good"}`}>
                {e.deltaUsd < 0 ? "−" : "+"}
                {formatUsd(Math.abs(e.deltaUsd))}
              </TCell>
              <TCell className="tabular-nums text-sub">{formatUsd(e.balanceAfterUsd)}</TCell>
            </TRow>
          ))}
        </tbody>
      </Table>
      <Pager page={page} totalPages={totalPages} onPage={onPage} />
    </>
  );
}
