"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { Mail } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";
import { requestPasswordReset } from "@/lib/auth";

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
      setError(err instanceof Error ? err.message : "Could not send the reset email. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg flex flex-col items-center justify-center px-4 py-10">
      <Reveal className="w-full max-w-sm">
        <Card className="p-8">
          <div className="flex justify-center mb-6">
            <Logo size={26} />
          </div>
          <h1 className="font-display text-xl text-ink text-center">Reset your password</h1>
          {sent ? (
            <p className="text-sm text-sub text-center mt-1.5">
              If an account exists for <span className="text-ink">{email}</span>, a reset link is on
              its way. Open it in this browser.
            </p>
          ) : (
            <>
              <p className="text-sm text-sub text-center mt-1.5 mb-6">
                We will email you a link to set a new password.
              </p>
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
                  <Mail size={15} /> {busy ? "Sending…" : "Send reset link"}
                </Button>
              </form>
            </>
          )}
          <p className="text-sm text-sub text-center mt-6">
            <Link href="/login" className="text-accent hover:text-accent-hi transition-colors">
              Back to sign in
            </Link>
          </p>
        </Card>
      </Reveal>
    </main>
  );
}
