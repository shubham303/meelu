"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { AuthShell, VerifyEmailForm, errorText } from "@demo/components/auth-screen";
import { Button, Field, Input } from "@demo/components/ui";
import {
  AuthFailure,
  resendVerificationCode,
  signInWithPassword,
  verifyEmailCode,
  type MeeluSession,
} from "@demo/lib/auth";

const linkClass = "text-accent hover:text-accent-hi transition-colors";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(false);

  function enter(session: MeeluSession) {
    router.push(session.created ? "/demo/onboarding" : "/demo/dashboard");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      enter(await signInWithPassword(email, password));
    } catch (err) {
      if (err instanceof AuthFailure && err.code === "EMAIL_NOT_VERIFIED") {
        setVerifying(true);
      } else {
        setError(errorText(err, "Sign in failed. Please try again."));
      }
      setBusy(false);
    }
  }

  if (verifying) {
    return (
      <AuthShell
        title="Confirm your email"
        subtitle="Your account is not confirmed yet."
        footer={
          <button type="button" className={linkClass} onClick={() => setVerifying(false)}>
            Back to sign in
          </button>
        }
      >
        <VerifyEmailForm
          email={email}
          onVerify={async (code) => enter(await verifyEmailCode(email, code))}
          onResend={() => resendVerificationCode(email)}
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in — your coworker's latest work is waiting."
      footer={
        <>
          <p>
            <Link href="/demo/forgot-password" className={linkClass}>
              Forgot password?
            </Link>
          </p>
          <p>
            New to Meelu?{" "}
            <Link href="/demo/signup" className={linkClass}>
              Create an account
            </Link>
          </p>
        </>
      }
    >
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
        <Field label="Password">
          <Input
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        {error && <p className="text-sm text-bad">{error}</p>}
        <Button type="submit" disabled={busy} className="w-full">
          <LogIn size={15} /> {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </AuthShell>
  );
}
