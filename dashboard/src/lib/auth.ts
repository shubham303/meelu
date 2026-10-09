"use client";

import { supabaseBrowser } from "@/lib/supabase/client";

export interface MeeluSession {
  created: boolean;
}

export async function startMeeluSession(accessToken: string): Promise<MeeluSession> {
  const res = await fetch("/api/auth/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accessToken }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.error?.message ?? "Sign in failed. Please try again.");
  return { created: Boolean(body?.data?.created) };
}

export async function signInWithPassword(email: string, password: string): Promise<MeeluSession> {
  const { data, error } = await supabaseBrowser().auth.signInWithPassword({ email, password });
  if (error || !data.session) throw new Error(error?.message ?? "Wrong email or password.");
  return startMeeluSession(data.session.access_token);
}

export async function signUpWithPassword(
  name: string,
  email: string,
  password: string,
): Promise<MeeluSession | "confirm-email"> {
  const { data, error } = await supabaseBrowser().auth.signUp({
    email,
    password,
    options: {
      data: { full_name: name },
      emailRedirectTo: `${window.location.origin}/auth/callback?next=/onboarding`,
    },
  });
  if (error) throw new Error(error.message);
  if (!data.session) return "confirm-email";
  return startMeeluSession(data.session.access_token);
}

export async function signInWithGoogle(): Promise<void> {
  const { error } = await supabaseBrowser().auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: `${window.location.origin}/auth/callback` },
  });
  if (error) throw new Error(error.message);
}

export async function signOutEverywhere(): Promise<void> {
  await Promise.allSettled([
    fetch("/api/auth/logout", { method: "POST" }),
    supabaseBrowser().auth.signOut(),
  ]);
}
