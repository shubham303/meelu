"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.error?.message ?? "Sign up failed. Please try again.");
        return;
      }
      const login = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!login.ok) {
        setError("Account created, but sign in failed. Try signing in.");
        return;
      }
      router.push("/onboarding");
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
          <h1 className="font-display text-xl text-ink text-center">Meet your new coworker</h1>
          <p className="text-sm text-sub text-center mt-1.5 mb-6">
            Create your workspace — it takes a minute.
          </p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Field label="Name">
              <Input
                type="text"
                autoComplete="name"
                placeholder="Your name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Field>
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
            <Field label="Password" hint="At least 6 characters.">
              <Input
                type="password"
                autoComplete="new-password"
                placeholder="••••••••"
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>
            {error && <p className="text-sm text-bad">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full">
              <UserPlus size={15} /> {busy ? "Creating account…" : "Create account"}
            </Button>
          </form>
          <p className="text-sm text-sub text-center mt-5">
            Already have an account?{" "}
            <Link href="/login" className="text-accent hover:text-accent-hi transition-colors">
              Sign in
            </Link>
          </p>
        </Card>
      </Reveal>
    </main>
  );
}
