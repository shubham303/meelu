"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Inbox as InboxIcon, RefreshCw } from "lucide-react";
import {
  Badge,
  Button,
  Card,
  Drawer,
  EmptyState,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { PageEnter } from "@/components/animate";
import { formatRelative } from "@/lib/utils";
import { GLOBAL } from "@/lib/current-site";
import { useCurrentSite } from "@/lib/use-api";
import type { MailboxMessage, MailboxPage } from "../agent-tasks";

const PAGE_SIZE = 25;

export default function InboxPage() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const canRead = !!bridge?.mailboxList;
  const selected = useCurrentSite();
  const siteId = selected && selected !== GLOBAL ? selected : null;

  const [page, setPage] = useState(1);
  const [data, setData] = useState<MailboxPage | null>(null);
  const [loading, setLoading] = useState(canRead);
  const [error, setError] = useState<string | null>(null);

  const [openUid, setOpenUid] = useState<number | null>(null);
  const [message, setMessage] = useState<MailboxMessage | null>(null);
  const [reading, setReading] = useState(false);
  const [readError, setReadError] = useState<string | null>(null);

  const load = useCallback(
    async (p: number) => {
      if (!bridge?.mailboxList) return;
      setLoading(true);
      setError(null);
      const res = await bridge.mailboxList({ page: p, pageSize: PAGE_SIZE, siteId });
      setLoading(false);
      if ("error" in res) {
        setError(res.error);
        return;
      }
      setData(res);
      setPage(res.page);
    },
    [bridge, siteId],
  );

  useEffect(() => {
    if (!bridge?.mailboxList) return;
    let cancelled = false;
    void bridge.mailboxList({ page: 1, pageSize: PAGE_SIZE, siteId }).then((res) => {
      if (cancelled) return;
      setLoading(false);
      if ("error" in res) {
        setError(res.error);
        return;
      }
      setData(res);
      setPage(res.page);
    });
    return () => {
      cancelled = true;
    };
  }, [bridge, siteId]);

  const openMessage = async (uid: number) => {
    if (!bridge?.mailboxRead) return;
    setOpenUid(uid);
    setMessage(null);
    setReadError(null);
    setReading(true);
    const res = await bridge.mailboxRead({ uid, siteId });
    setReading(false);
    if ("error" in res) {
      setReadError(res.error);
      return;
    }
    setMessage(res);
  };

  if (!canRead) {
    return (
      <PageEnter>
        <PageHeader
          title="Inbox"
          description="Your connected mailbox, read in place — replies to your outreach land here."
        />
        <EmptyState
          icon={InboxIcon}
          title="The inbox lives in the Meelu app"
          hint="Your mailbox credential stays encrypted on your own device, so messages can only be read there — this website never sees them. Open the Meelu app to browse your inbox."
        />
      </PageEnter>
    );
  }

  return (
    <PageEnter>
      <PageHeader
        title="Inbox"
        description={
          data
            ? `${data.address} — ${data.total} message${data.total === 1 ? "" : "s"}. Read-only: replying happens through the agent flows, with your yes on the exact text.`
            : "Your connected mailbox, read in place."
        }
        actions={
          <Button variant="outline" size="sm" onClick={() => void load(page)} disabled={loading}>
            <RefreshCw size={13} className={loading ? "animate-spin" : undefined} /> Refresh
          </Button>
        }
      />

      {error && (
        <Card className="mb-4">
          <p className="text-sm text-bad">{error}</p>
          <p className="text-xs text-faint mt-1.5">
            The mailbox is connected on the{" "}
            <Link href="/dashboard/connections" className="text-accent hover:underline">
              Connections screen
            </Link>
            {" "}— address, app password, and (for custom domains) the IMAP host.
          </p>
        </Card>
      )}

      {loading && !data ? (
        <Spinner />
      ) : data && data.messages.length === 0 && !error ? (
        <EmptyState icon={InboxIcon} title="Nothing here" hint="This page of the mailbox is empty." />
      ) : data ? (
        <>
          <Card className="p-0 overflow-hidden">
            <ul className="divide-y divide-edge">
              {data.messages.map((m) => (
                <li key={m.uid}>
                  <button
                    type="button"
                    onClick={() => void openMessage(m.uid)}
                    className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-panel2 cursor-pointer"
                  >
                    <span
                      className={`h-1.5 w-1.5 shrink-0 rounded-full ${m.seen ? "bg-transparent" : "bg-accent"}`}
                      aria-label={m.seen ? undefined : "unread"}
                    />
                    <span
                      className={`w-52 shrink-0 truncate text-sm ${m.seen ? "text-sub" : "text-ink font-medium"}`}
                    >
                      {m.from ?? "(unknown sender)"}
                    </span>
                    <span
                      className={`min-w-0 grow truncate text-sm ${m.seen ? "text-sub" : "text-ink"}`}
                    >
                      {m.subject ?? "(no subject)"}
                    </span>
                    <span className="shrink-0 text-xs text-faint">
                      {m.date ? formatRelative(m.date) : ""}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-faint">
              Page {data.page} of {data.pages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => void load(page - 1)}
                disabled={loading || page <= 1}
              >
                <ChevronLeft size={13} /> Newer
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void load(page + 1)}
                disabled={loading || page >= data.pages}
              >
                Older <ChevronRight size={13} />
              </Button>
            </div>
          </div>
        </>
      ) : null}

      <Drawer
        open={openUid !== null}
        onClose={() => setOpenUid(null)}
        title={message?.subject ?? "Message"}
      >
        {reading ? (
          <Spinner />
        ) : readError ? (
          <p className="text-sm text-bad">{readError}</p>
        ) : message ? (
          <div className="space-y-4">
            <div className="space-y-1 text-sm">
              <p className="text-ink">{message.from ?? "(unknown sender)"}</p>
              {message.to && <p className="text-faint text-xs">to {message.to}</p>}
              {message.date && (
                <p className="text-faint text-xs">{new Date(message.date).toLocaleString()}</p>
              )}
            </div>
            {message.attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {message.attachments.map((a, i) => (
                  <Badge key={i} tone="neutral">
                    {a.filename}
                  </Badge>
                ))}
              </div>
            )}
            <pre className="whitespace-pre-wrap break-words font-sans text-sm text-sub leading-relaxed">
              {message.body || "(no text body)"}
            </pre>
          </div>
        ) : null}
      </Drawer>
    </PageEnter>
  );
}
