import type { Metadata } from "next";
import { DownloadButtons } from "@/components/download-buttons";
import { site } from "@/lib/site";

const title = "Download the Meelu desktop app for macOS and Windows";
const description =
  "Meelu's desktop app is where the agent works. It runs crawls and the agent on your own computer and connects to your Meelu account. For macOS and Windows.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}/download` },
  openGraph: { title, description, url: `${site.url}/download`, type: "website" },
};

export default function DownloadPage() {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-edge">
        <div aria-hidden className="grain absolute inset-0" />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(55% 45% at 50% 0%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto w-full max-w-4xl px-6 py-16 text-center sm:py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Desktop app
          </p>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Download Meelu
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-sub text-pretty sm:text-lg">
            The desktop app is where the agent works. It runs crawls and the
            agent on your own computer, and connects to your Meelu account.
          </p>
          <div className="mt-10">
            <DownloadButtons />
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-6 py-16">
        <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
          First launch
        </p>
        <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
          Your computer will warn you once
        </h2>
        <p className="mt-4 max-w-2xl text-base text-sub text-pretty">
          The app is not signed by Apple or Microsoft yet, so the first time you
          open it your system will ask if you trust it.
        </p>
        <div className="mt-8 grid gap-5 sm:grid-cols-2">
          <div className="rounded-2xl border border-edge bg-panel p-6">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              macOS
            </p>
            <p className="mt-3 text-sm text-sub">
              Right-click Meelu in Applications and choose{" "}
              <span className="text-ink">Open</span>. Or go to{" "}
              <span className="text-ink">
                System Settings → Privacy &amp; Security
              </span>{" "}
              and click <span className="text-ink">Open Anyway</span>.
            </p>
          </div>
          <div className="rounded-2xl border border-edge bg-panel p-6">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              Windows
            </p>
            <p className="mt-3 text-sm text-sub">
              When SmartScreen appears, click{" "}
              <span className="text-ink">More info</span>, then{" "}
              <span className="text-ink">Run anyway</span>.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
