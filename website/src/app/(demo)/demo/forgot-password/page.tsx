"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound, Mail } from "lucide-react";
import {
  AuthShell,
  CodeInput,
  RESEND_COOLDOWN_SECONDS,
  ResendButton,
  errorText,
  useCooldown,
} from "@demo/components/auth-screen";
import { Button, Field, Input } from "@demo/components/ui";
import { requestPasswordReset, resetPasswordWithCode } from "@demo/lib/auth";

const linkClass = "text-accent hover:text-accent-hi transition-colors";

function ResetForm({ email }: { email: string }) {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [resending, setResending] = useState(false);
  const [secondsLeft, restartCooldown] = useCooldown(RESEND_COOLDOWN_SECONDS);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const session = await resetPasswordWithCode(email, code, password);
      router.push(session.created ? "/demo/onboarding" : "/demo/dashboard");
    } catch (err) {
      setError(errorText(err, "Could not set the new password. Please try again."));
      setBusy(false);
    }
  }

  async function handleResend() {
    setError(null);
    setNotice(null);
    setResending(true);
    try {
      await requestPasswordReset(email);
      setCode("");
      setNotice("A new code is on its way.");
      restartCooldown();
    } catch (err) {
      setError(errorText(err, "Could not send a new code. Please try again."));
    } finally {
      setResending(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-sub text-center">
        If an account exists for <span className="text-ink">{email}</span>, a 6-digit code is on its
        way. It expires in 10 minutes.
      </p>
      <Field label="Code">
        <CodeInput value={code} onChange={setCode} />
      </Field>
      <Field label="New password" hint="At least 8 characters.">
        <Input
          type="password"
          autoComplete="new-password"
          minLength={8}
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </Field>
      {error && <p className="text-sm text-bad">{error}</p>}
      {notice && <p className="text-sm text-good">{notice}</p>}
      <Button type="submit" disabled={busy || code.length !== 6} className="w-full">
        <KeyRound size={15} /> {busy ? "Saving…" : "Set new password"}
      </Button>
      <div className="flex justify-center">
        <ResendButton secondsLeft={secondsLeft} busy={resending} onResend={handleResend} />
      </div>
    </form>
  );
}

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(errorText(err, "Could not send the reset code. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title="Reset your password"
      subtitle={sent ? undefined : "We will email you a code to set a new password."}
      footer={
        <p>
          <Link href="/demo/login" className={linkClass}>
            Back to sign in
          </Link>
        </p>
      }
    >
      {sent ? (
        <div className="mt-6">
          <ResetForm email={email} />
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <Field label="Email">
            <Input
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </Field>
          {error && <p className="text-sm text-bad">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            <Mail size={15} /> {busy ? "Sending…" : "Send reset code"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
