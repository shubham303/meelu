"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus } from "lucide-react";
import { Logo } from "@/components/logo";
import { Reveal } from "@/components/animate";
import { Button, Card, Field, Input } from "@/components/ui";
import { GoogleButton, OrDivider } from "@/components/google-button";
import { signUpWithPassword } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setBusy(true);
    try {
      const result = await signUpWithPassword(name, email, password);
      if (result === "confirm-email") {
        setSentTo(email);
        return;
      }
      router.push(result.created ? "/onboarding" : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign up failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <main className="min-h-screen bg-bg flex flex-col items-center justify-center px-4 py-10">
        <Reveal className="w-full max-w-sm">
          <Card className="p-8 text-center">
            <div className="flex justify-center mb-6">
              <Logo size={26} />
            </div>
            <h1 className="font-display text-xl text-ink">Check your email</h1>
            <p className="text-sm text-sub mt-1.5">
              We sent a confirmation link to <span className="text-ink">{sentTo}</span>. Open it
              to finish creating your workspace.
            </p>
          </Card>
        </Reveal>
      </main>
    );
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
          <GoogleButton onError={setError} />
          <OrDivider />
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
