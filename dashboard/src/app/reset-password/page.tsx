"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, KeyRound } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";
import { beginPasswordReset, setNewPassword } from "@/lib/auth";
import { useIsApp } from "@/lib/use-app-mode";

const EXPIRED = "This reset link has expired. Request a new one.";

function recoveryTokens(): { accessToken: string; refreshToken: string } | null {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  if (params.get("type") !== "recovery" || !accessToken || !refreshToken) return null;
  return { accessToken, refreshToken };
}

export default function ResetPasswordPage() {
  const router = useRouter();
  const isApp = useIsApp();
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [updated, setUpdated] = useState(false);
  const exchanged = useRef(false);

  useEffect(() => {
    if (exchanged.current) return;
    exchanged.current = true;
    const tokens = recoveryTokens();
    window.history.replaceState(null, "", window.location.pathname);
    beginPasswordReset(tokens)
      .then(() => setReady(true))
      .catch((err) => setError(err instanceof Error ? err.message : EXPIRED));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const session = await setNewPassword(password);
      if (isApp) router.push(session.created ? "/onboarding" : "/dashboard");
      else setUpdated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not set the new password.");
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
          {updated ? (
            <div className="text-center">
              <CheckCircle2 size={28} className="mx-auto text-good" />
              <h1 className="font-display text-xl text-ink mt-3">Password updated</h1>
              <p className="text-sm text-sub mt-1.5">
                Open the Meelu app and sign in with your new password.
              </p>
            </div>
          ) : (
            <>
              <h1 className="font-display text-xl text-ink text-center mb-6">Choose a new password</h1>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Field label="New password">
                  <Input
                    type="password"
                    autoComplete="new-password"
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={!ready}
                    required
                  />
                </Field>
                {error && <p className="text-sm text-bad">{error}</p>}
                <Button type="submit" disabled={busy || !ready} className="w-full">
                  <KeyRound size={15} /> {busy ? "Saving…" : "Set password"}
                </Button>
              </form>
              <p className="text-sm text-sub text-center mt-6">
                {isApp ? (
                  <Link href="/forgot-password" className="text-accent hover:text-accent-hi transition-colors">
                    Request a new link
                  </Link>
                ) : (
                  "Need a new link? Request one from the Meelu app."
                )}
              </p>
            </>
          )}
        </Card>
      </Reveal>
    </main>
  );
}
