"use client";

import { useEffect } from "react";
import { useApi } from "./use-api";

const POLL_MS = 60_000;

export interface Balance {
  balanceMicros: number;
  balanceUsd: number;
}

export function useCredits() {
  const balance = useApi<Balance>("/api/v1/credits");
  const { refresh } = balance;

  useEffect(() => {
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    const timer = setInterval(onFocus, POLL_MS);
    const detach = window.meeluAgent?.onEvent?.((m) => {
      if (m.event === "done") onFocus();
    });
    return () => {
      window.removeEventListener("focus", onFocus);
      clearInterval(timer);
      detach?.();
    };
  }, [refresh]);

  return balance;
}
