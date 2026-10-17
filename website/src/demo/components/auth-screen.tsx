"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { MailCheck, RotateCw } from "lucide-react";
import { Logo } from "@demo/components/logo";
import { Reveal } from "@demo/components/animate";
import { Button, Card, Field, Input } from "@demo/components/ui";

export const RESEND_COOLDOWN_SECONDS = 60;

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-bg flex flex-col items-center justify-center px-4 py-10">
      <Reveal className="w-full max-w-sm">
        <Card className="p-8">
          <div className="flex justify-center mb-6">
            <Logo size={26} />
          </div>
          <h1 className="font-display text-xl text-ink text-center">{title}</h1>
          {subtitle && <p className="text-sm text-sub text-center mt-1.5 mb-6">{subtitle}</p>}
          {children}
          {footer && <div className="text-sm text-sub text-center mt-6 space-y-2">{footer}</div>}
        </Card>
      </Reveal>
    </main>
  );
}

export function errorText(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}

export function useCooldown(initial: number): [number, () => void] {
  const [left, setLeft] = useState(initial);
  useEffect(() => {
    if (left <= 0) return;
    const timer = setTimeout(() => setLeft((s) => s - 1), 1000);
    return () => clearTimeout(timer);
  }, [left]);
  return [left, () => setLeft(RESEND_COOLDOWN_SECONDS)];
}

export function CodeInput({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Input
      inputMode="numeric"
      autoComplete="one-time-code"
      pattern="[0-9]{6}"
      maxLength={6}
      placeholder="123456"
      className="text-center tracking-[0.4em] font-mono"
      value={value}
      onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, 6))}
      required
    />
  );
}

export function ResendButton({
  secondsLeft,
  busy,
  onResend,
}: {
  secondsLeft: number;
  busy: boolean;
  onResend: () => void;
}) {
  return (
    <Button type="button" variant="ghost" size="sm" disabled={busy || secondsLeft > 0} onClick={onResend}>
      <RotateCw size={13} /> {secondsLeft > 0 ? `Send a new code in ${secondsLeft}s` : "Send a new code"}
    </Button>
  );
}

export function VerifyEmailForm({
  email,
  onVerify,
  onResend,
}: {
  email: string;
  onVerify: (code: string) => Promise<void>;
  onResend: () => Promise<void>;
}) {
  const [code, setCode] = useState("");
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
      await onVerify(code);
    } catch (err) {
      setError(errorText(err, "Could not check the code. Please try again."));
      setBusy(false);
    }
  }

  async function handleResend() {
    setError(null);
    setNotice(null);
    setResending(true);
    try {
      await onResend();
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
        We sent a 6-digit code to <span className="text-ink">{email}</span>. It expires in 10 minutes.
      </p>
      <Field label="Code">
        <CodeInput value={code} onChange={setCode} />
      </Field>
      {error && <p className="text-sm text-bad">{error}</p>}
      {notice && <p className="text-sm text-good">{notice}</p>}
      <Button type="submit" disabled={busy || code.length !== 6} className="w-full">
        <MailCheck size={15} /> {busy ? "Checking…" : "Confirm email"}
      </Button>
      <div className="flex justify-center">
        <ResendButton secondsLeft={secondsLeft} busy={resending} onResend={handleResend} />
      </div>
    </form>
  );
}
