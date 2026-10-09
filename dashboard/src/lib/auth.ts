"use client";

import type { AuthError } from "@supabase/supabase-js";
import { supabaseBrowser } from "@/lib/supabase/client";

export interface MeeluSession {
  created: boolean;
}

export async function startMeeluSession(accessToken: string): Promise<MeeluSession> {
  try {
    const res = await fetch("/api/auth/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accessToken }),
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error(body?.error?.message ?? "Sign in failed. Please try again.");
    return { created: Boolean(body?.data?.created) };
  } finally {
    await supabaseBrowser().auth.signOut({ scope: "local" });
  }
}

function signInMessage(error: AuthError | null): string {
  if (error?.code === "invalid_credentials") return "Wrong email or password.";
  if (error?.code === "email_not_confirmed") return "Confirm your email address before signing in.";
  if (error?.status === 429) return "Too many attempts. Wait a minute and try again.";
  return "Sign in failed. Please try again.";
}

export async function signInWithPassword(email: string, password: string): Promise<MeeluSession> {
  const { data, error } = await supabaseBrowser().auth.signInWithPassword({ email, password });
  if (error || !data.session) throw new Error(signInMessage(error));
  return startMeeluSession(data.session.access_token);
}

export async function requestPasswordReset(email: string): Promise<void> {
  const { error } = await supabaseBrowser().auth.resetPasswordForEmail(email, {
    redirectTo: `${window.location.origin}/reset-password`,
  });
  if (error?.status === 429) throw new Error("Too many attempts. Wait a minute and try again.");
}

export async function beginPasswordReset(code: string): Promise<void> {
  const { error } = await supabaseBrowser().auth.exchangeCodeForSession(code);
  if (error) {
    throw new Error("This reset link has expired or was opened in another browser. Request a new one.");
  }
}

export async function setNewPassword(password: string): Promise<MeeluSession> {
  const { data, error } = await supabaseBrowser().auth.updateUser({ password });
  if (error) throw new Error(error.message);
  const session = await supabaseBrowser().auth.getSession();
  const token = session.data.session?.access_token;
  if (!data.user || !token) throw new Error("This reset link has expired. Request a new one.");
  return startMeeluSession(token);
}

export async function signOutEverywhere(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
}
