"use client";

import { use, useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";
import { beginPasswordReset, setNewPassword } from "@/lib/auth";

const EXPIRED = "This reset link has expired. Request a new one.";

export default function ResetPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string }>;
}) {
  const router = useRouter();
  const { code } = use(searchParams);
  const [ready, setReady] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(code ? null : EXPIRED);
  const [busy, setBusy] = useState(false);
  const exchanged = useRef(false);

  useEffect(() => {
    if (!code || exchanged.current) return;
    exchanged.current = true;
    beginPasswordReset(code)
      .then(() => setReady(true))
      .catch((err) => setError(err instanceof Error ? err.message : EXPIRED));
  }, [code]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const session = await setNewPassword(password);
      router.push(session.created ? "/onboarding" : "/dashboard");
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
            <Link href="/forgot-password" className="text-accent hover:text-accent-hi transition-colors">
              Request a new link
            </Link>
          </p>
        </Card>
      </Reveal>
    </main>
  );
}
