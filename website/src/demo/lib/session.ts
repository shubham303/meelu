"use client";

import { USER } from "@demo/mock/data/misc";

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
  return { data: { user: USER }, isPending: false };
}

export async function signOut(): Promise<void> {
  const top = window.top ?? window;
  top.location.href = "/download";
}
