"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, BrainCircuit, UserRound } from "lucide-react";
import { gsap, useGSAP, Reveal } from "@/components/animate";
import { Logo } from "@/components/logo";
import { Button, Card, Field, Input, Textarea } from "@/components/ui";
import { api } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import type { UserProfile } from "@/lib/types";

export default function OnboardingPage() {
  const router = useRouter();
  const isApp = useIsApp();
  const stepRef = useRef<HTMLDivElement>(null);

  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("");
  const [timezone, setTimezone] = useState("");
  const [signature, setSignature] = useState("");
  const [writingVoice, setWritingVoice] = useState("");

  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useGSAP(
    () => {
      if (!stepRef.current) return;
      gsap.fromTo(
        stepRef.current,
        { autoAlpha: 0, y: 12 },
        { autoAlpha: 1, y: 0, duration: 0.5, ease: "power3.out" },
      );
    },
    { dependencies: [] },
  );

  useEffect(() => {
    let live = true;
    void api<UserProfile | null>("/api/v1/profile")
      .then((p) => {
        if (!live || !p) return;
        setFullName(p.fullName ?? "");
        setRole(p.role ?? "");
        setTimezone(p.timezone ?? "");
        setSignature(p.signature ?? "");
        setWritingVoice(p.writingVoice ?? "");
      })
      .catch(() => {
      });
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (timezone) return;
    try {
      const guess = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (guess?.includes("/")) setTimezone(guess);
    } catch {
    }
  }, [timezone]);

  const canFinish = fullName.trim().length > 0;

  async function finish() {
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/profile", {
        method: "PUT",
        body: {
          fullName: fullName.trim(),
          role: role.trim(),
          timezone: timezone.trim(),
          signature,
          writingVoice: writingVoice.trim(),
        },
      });
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg flex flex-col items-center justify-center px-4 py-10">
      <Reveal className="w-full max-w-xl">
        <div className="flex justify-center mb-8">
          <Logo size={26} />
        </div>

        <Card className="p-8">
          <div ref={stepRef}>
            <div className="flex items-center gap-2.5 mb-1">
              <span className="rounded-lg bg-accent-soft p-1.5">
                <UserRound className="text-accent" size={16} />
              </span>
              <span className="text-xs text-faint uppercase tracking-wide">Let&apos;s begin</span>
            </div>
            <h1 className="font-display text-xl text-ink mb-1">Who should Meelu write as?</h1>
            <p className="text-sm text-sub mb-5">
              This is you, not your business — it stays the same however many websites you run.
            </p>

            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Your name">
                  <Input
                    type="text"
                    placeholder="e.g. Shubham Randive"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </Field>
                <Field label="Role" hint="How you're introduced.">
                  <Input
                    type="text"
                    placeholder="e.g. Founder"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  />
                </Field>
              </div>

              <Field label="Timezone" hint='An IANA name — "Asia/Kolkata", not "IST".'>
                <Input
                  type="text"
                  placeholder="e.g. Asia/Kolkata"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                />
              </Field>

              <Field
                label="How you sign off"
                hint="Used word for word at the bottom of every outreach email."
              >
                <Textarea
                  rows={3}
                  placeholder={"Thanks,\nShubham"}
                  value={signature}
                  onChange={(e) => setSignature(e.target.value)}
                />
              </Field>

              <Field label="How you want to come across" hint="In your own words.">
                <Textarea
                  rows={3}
                  placeholder="e.g. Plain-spoken and direct. Short sentences, no jargon, never salesy."
                  value={writingVoice}
                  onChange={(e) => setWritingVoice(e.target.value)}
                />
              </Field>

              <Card className="bg-panel2 border-edge2 p-4">
                <div className="flex items-start gap-3">
                  <BrainCircuit className="text-accent shrink-0 mt-0.5" size={16} />
                  <p className="text-xs text-sub leading-relaxed">
                    Only your name is needed now — the rest you can fill in later from Settings
                    {isApp ? ", or by asking your coworker to set it up" : ""}. Next, add the
                    website you want worked on from the switcher at the top of the dashboard.
                  </p>
                </div>
              </Card>
            </div>

            {error && <p className="text-sm text-bad mt-4">{error}</p>}

            <div className="flex items-center justify-end mt-7">
              <Button onClick={finish} disabled={busy || !canFinish}>
                {busy ? "Saving…" : "Open my dashboard"} <ArrowRight size={15} />
              </Button>
            </div>
          </div>
        </Card>
      </Reveal>
    </main>
  );
}
