"use client";

import { useEffect, useState } from "react";
import { useApi, useCurrentSite } from "@/lib/use-api";
import type { SiteProfile } from "@/lib/types";

export interface SendingAs {
  address: string | null;
  intended: string | null;
  bound: boolean;
  missing: boolean;
  ambiguous: boolean;
  none: boolean;
  unknown: boolean;
  line: string;
}

const EMPTY: SendingAs = {
  address: null,
  intended: null,
  bound: false,
  missing: false,
  ambiguous: false,
  none: false,
  unknown: true,
  line: "mailbox: not readable from here",
};

export function canSend(mb: SendingAs): boolean {
  return !mb.unknown && !mb.missing && !mb.ambiguous && !mb.none && mb.address !== null;
}

export function useSendingAs(): SendingAs {
  const siteId = useCurrentSite();
  const { data: site } = useApi<SiteProfile>(siteId ? `/sites/${siteId}` : null);
  const [accounts, setAccounts] = useState<string[] | null>(null);

  useEffect(() => {
    let live = true;
    const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
    if (!bridge?.getMailboxAccounts) {
      setAccounts(null);
      return;
    }
    void bridge
      .getMailboxAccounts()
      .then((res) => {
        if (!live) return;
        if (!res || "error" in res) return setAccounts(null);
        setAccounts(res.accounts.map((a) => a.id));
      })
      .catch(() => {
        if (live) setAccounts(null);
      });
    return () => {
      live = false;
    };
  }, []);

  const intended: string | null = null;

  if (accounts === null) {
    return {
      ...EMPTY,
      intended,
      line: intended ? `mailbox: ${intended} (sending happens in the app)` : EMPTY.line,
    };
  }

  if (intended) {
    const here = accounts.includes(intended);
    return {
      address: here ? intended : null,
      intended,
      bound: here,
      missing: !here,
      ambiguous: false,
      none: false,
      unknown: false,
      line: here ? `mailbox: ${intended}` : `mailbox: ${intended} — not connected on this device`,
    };
  }

  if (accounts.length === 1) {
    return {
      address: accounts[0],
      intended: null,
      bound: false,
      missing: false,
      ambiguous: false,
      none: false,
      unknown: false,
      line: `mailbox: ${accounts[0]}`,
    };
  }

  return {
    address: null,
    intended: null,
    bound: false,
    missing: false,
    ambiguous: accounts.length > 1,
    none: accounts.length === 0,
    unknown: false,
    line:
      accounts.length > 1
        ? "mailbox: several on this device, none chosen for this website"
        : "mailbox: none connected",
  };
}

export function sendingAsSentence(mb: SendingAs): string {
  if (mb.unknown) {
    return mb.intended
      ? `This website sends as ${mb.intended}. Sending itself happens in the Meelu app, with the credential on your own device.`
      : "Sending happens in the Meelu app, with your own mailbox on your own device.";
  }
  if (mb.missing) {
    return `This website sends as ${mb.intended}, but no credential for it is connected on this device. Connect that mailbox in Settings, or change the website's sending address — it will not send as anything else.`;
  }
  if (mb.ambiguous) {
    return "Several mailboxes on this device and none chosen for this website. It will not guess — pick one in Settings, because outreach signed as the wrong business is worse than outreach not sent.";
  }
  if (mb.none) {
    return "No mailbox connected. Connect one in Settings; the credential never leaves this machine.";
  }
  return mb.bound
    ? `${mb.address} — this website's own address. A different business sends as itself.`
    : `${mb.address} — the only mailbox on this device. Set it as this website's address in Settings once you run a second business here.`;
}
