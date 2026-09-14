"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogIn } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.error?.message ?? "Sign in failed. Check your email and password.");
        return;
      }
      router.push("/dashboard");
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
          <h1 className="font-display text-xl text-ink text-center">Welcome back</h1>
          <p className="text-sm text-sub text-center mt-1.5 mb-6">
            Sign in — your coworker&apos;s latest work is waiting.
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
          <p className="text-sm text-sub text-center mt-6">
            New to Meelu?{" "}
            <Link href="/signup" className="text-accent hover:text-accent-hi transition-colors">
              Create an account
            </Link>
          </p>
        </Card>
      </Reveal>
    </main>
  );
}
