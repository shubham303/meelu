"use client";

import { useEffect, useState } from "react";
import { signOutEverywhere } from "@/lib/auth";

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  image: string | null;
}

export interface Session {
  user: SessionUser;
}

export function useSession(): { data: Session | null; isPending: boolean } {
  const [data, setData] = useState<Session | null>(null);
  const [isPending, setPending] = useState(true);

  useEffect(() => {
    let live = true;
    void (async () => {
      try {
        const res = await fetch("/api/auth/me", { cache: "no-store" });
        if (!live) return;
        if (!res.ok) {
          setData(null);
          return;
        }
        const body = (await res.json()) as { data?: SessionUser };
        setData(body.data ? { user: body.data } : null);
      } catch {
        if (live) setData(null);
      } finally {
        if (live) setPending(false);
      }
    })();
    return () => {
      live = false;
    };
  }, []);

  return { data, isPending };
}

export async function signOut(): Promise<void> {
  await signOutEverywhere();
  window.location.href = "/login";
}
