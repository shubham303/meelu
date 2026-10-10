"use client";

import { createAuthClient } from "better-auth/client";
import { emailOTPClient, jwtClient } from "better-auth/client/plugins";

function buildClient() {
  return createAuthClient({
    baseURL: window.location.origin,
    basePath: "/auth",
    plugins: [emailOTPClient(), jwtClient()],
  });
}

let client: ReturnType<typeof buildClient> | undefined;

function authClient(): ReturnType<typeof buildClient> {
  client ??= buildClient();
  return client;
}

export interface MeeluSession {
  created: boolean;
}

export class AuthFailure extends Error {
  constructor(
    message: string,
    readonly code: string | null,
  ) {
    super(message);
  }
}

interface ClientError {
  code?: string;
  status?: number;
  message?: string;
}

const MESSAGES: Record<string, string> = {
  INVALID_EMAIL_OR_PASSWORD: "Wrong email or password.",
  EMAIL_NOT_VERIFIED: "Confirm your email address first. We sent you a new code.",
  USER_ALREADY_EXISTS: "An account with this email already exists. Sign in instead.",
  SIGNUPS_FULL: "Sign-ups are full right now.",
  INVALID_EMAIL: "Enter a valid email address.",
  PASSWORD_TOO_SHORT: "Enter a password.",
  PASSWORD_TOO_LONG: "That password is too long.",
  INVALID_OTP: "That code is not right. Check it and try again.",
  OTP_EXPIRED: "That code has expired. Send a new one.",
  TOO_MANY_ATTEMPTS: "Too many wrong codes. Send a new one.",
};

function failure(error: ClientError, fallback: string): AuthFailure {
  if (error.status === 429) {
    return new AuthFailure("Too many attempts. Wait a minute and try again.", "RATE_LIMITED");
  }
  const code = error.code ?? null;
  return new AuthFailure((code && MESSAGES[code]) || fallback, code);
}

async function startMeeluSession(accessToken: string): Promise<MeeluSession> {
  const res = await fetch("/api/auth/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ accessToken }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new AuthFailure(body?.error?.message ?? "Sign in failed. Please try again.", null);
  return { created: Boolean(body?.data?.created) };
}

async function finishSignIn(): Promise<MeeluSession> {
  const auth = authClient();
  try {
    const { data, error } = await auth.token();
    if (error || !data?.token) throw failure(error ?? {}, "Sign in failed. Please try again.");
    return await startMeeluSession(data.token);
  } finally {
    await auth.signOut().catch(() => undefined);
  }
}

export async function signInWithPassword(email: string, password: string): Promise<MeeluSession> {
  const { error } = await authClient().signIn.email({ email, password });
  if (error) throw failure(error, "Sign in failed. Please try again.");
  return finishSignIn();
}

export async function signUpWithPassword(name: string, email: string, password: string): Promise<void> {
  const { error } = await authClient().signUp.email({ name: name.trim(), email, password });
  if (error) throw failure(error, "Sign up failed. Please try again.");
}

export async function verifyEmailCode(email: string, otp: string): Promise<MeeluSession> {
  const { error } = await authClient().emailOtp.verifyEmail({ email, otp: otp.trim() });
  if (error) throw failure(error, "Could not check the code. Please try again.");
  return finishSignIn();
}

export async function resendVerificationCode(email: string): Promise<void> {
  const { error } = await authClient().emailOtp.sendVerificationOtp({ email, type: "email-verification" });
  if (error) throw failure(error, "Could not send a new code. Please try again.");
}

export async function requestPasswordReset(email: string): Promise<void> {
  const { error } = await authClient().emailOtp.requestPasswordReset({ email });
  if (error) throw failure(error, "Could not send the reset code. Please try again.");
}

export async function resetPasswordWithCode(
  email: string,
  otp: string,
  password: string,
): Promise<MeeluSession> {
  const { error } = await authClient().emailOtp.resetPassword({ email, otp: otp.trim(), password });
  if (error) throw failure(error, "Could not set the new password. Please try again.");
  return signInWithPassword(email, password);
}

export async function signOutEverywhere(): Promise<void> {
  await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
}
