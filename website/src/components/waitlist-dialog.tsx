"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { CircleAlert, CircleCheck, X } from "lucide-react";
import { USER_CAP } from "@/lib/waitlist/cap";

type Status =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "joined"; email: string }
  | { kind: "error"; message: string };

export function WaitlistDialog({
  open,
  platform,
  onClose,
}: {
  open: boolean;
  platform: string;
  onClose: () => void;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus({ kind: "sending" });
    try {
      const response = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, platform, company }),
      });
      const data = (await response.json().catch(() => ({}))) as { message?: string };
      if (!response.ok) {
        setStatus({ kind: "error", message: data.message ?? "Something went wrong. Please try again." });
        return;
      }
      setStatus({ kind: "joined", email: email.trim() });
    } catch {
      setStatus({ kind: "error", message: "We could not reach the server. Check your connection and try again." });
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-edge bg-panel p-0 text-left text-ink shadow-xl backdrop:bg-black/50"
    >
      <div className="relative p-6">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-4 top-4 rounded-md p-1 text-faint transition-colors hover:text-ink"
        >
          <X size={18} />
        </button>

        {status.kind === "joined" ? (
          <div className="flex flex-col items-start gap-3 pr-6">
            <CircleCheck size={22} className="text-accent" />
            <h2 className="font-display text-xl tracking-tight text-ink">You are on the waitlist</h2>
            <p className="text-sm text-sub text-pretty">
              We will email <span className="text-ink">{status.email}</span> when the next batch
              opens.
            </p>
            <button
              type="button"
              onClick={onClose}
              className="mt-2 inline-flex h-10 items-center rounded-lg border border-edge px-4 text-sm font-medium text-ink transition-colors hover:bg-panel2"
            >
              Done
            </button>
          </div>
        ) : (
          <>
            <div className="flex items-start gap-3 pr-6">
              <CircleAlert size={20} className="mt-0.5 shrink-0 text-warn" />
              <div>
                <h2 className="font-display text-xl tracking-tight text-ink">Download failed</h2>
                <p className="mt-2 text-sm text-sub text-pretty">
                  We have reached the current cap of {USER_CAP} users. Join the waitlist to be in
                  the next batch.
                </p>
              </div>
            </div>

            <form onSubmit={submit} className="mt-6 flex flex-col gap-3">
              <label htmlFor="waitlist-email" className="text-xs font-medium text-sub">
                Email
              </label>
              <input
                id="waitlist-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                className="h-11 w-full rounded-lg border border-edge bg-transparent px-3 text-base text-ink outline-none transition-colors placeholder:text-faint focus:border-accent sm:text-sm"
              />
              <input
                type="text"
                name="company"
                tabIndex={-1}
                autoComplete="off"
                aria-hidden
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                className="hidden"
              />
              {status.kind === "error" && (
                <p className="text-sm text-warn">{status.message}</p>
              )}
              <button
                type="submit"
                disabled={status.kind === "sending"}
                className="inline-flex h-11 items-center justify-center rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
              >
                {status.kind === "sending" ? "Joining…" : "Join the waitlist"}
              </button>
            </form>
          </>
        )}
      </div>
    </dialog>
  );
}
