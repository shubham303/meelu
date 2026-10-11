"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { UserPlus } from "lucide-react";
import { AuthShell, VerifyEmailForm, errorText } from "@/components/auth-screen";
import { Button, Field, Input } from "@/components/ui";
import { resendVerificationCode, signUpWithPassword, verifyEmailCode } from "@/lib/auth";

const linkClass = "text-accent hover:text-accent-hi transition-colors";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [verifying, setVerifying] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signUpWithPassword(name, email, password);
      setVerifying(true);
    } catch (err) {
      setError(errorText(err, "Sign up failed. Please try again."));
    } finally {
      setBusy(false);
    }
  }

  if (verifying) {
    return (
      <AuthShell
        title="Confirm your email"
        subtitle="One last step before you start."
        footer={
          <button type="button" className={linkClass} onClick={() => setVerifying(false)}>
            Use a different email
          </button>
        }
      >
        <VerifyEmailForm
          email={email}
          onVerify={async (code) => {
            const session = await verifyEmailCode(email, code);
            router.push(session.created ? "/onboarding" : "/dashboard");
          }}
          onResend={() => resendVerificationCode(email)}
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Meelu watches your site and suggests what to do next."
      footer={
        <p>
          Already have an account?{" "}
          <Link href="/login" className={linkClass}>
            Sign in
          </Link>
        </p>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Name (optional)">
          <Input
            type="text"
            autoComplete="name"
            placeholder="Ada Lovelace"
            value={name}
            onChange={(e) => setName(e.target.value)}
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
        <Field label="Password" hint="At least 8 characters.">
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
        <Button type="submit" disabled={busy} className="w-full">
          <UserPlus size={15} /> {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthShell>
  );
}
