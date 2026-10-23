import type { Metadata } from "next";
import { TriangleAlert } from "lucide-react";
import { DownloadButtons } from "@/components/download-buttons";
import { site } from "@/lib/site";
import { softwareApplicationJson } from "@/lib/software-schema";

const title = "Download the Meelu desktop app (beta) for macOS and Windows";
const description =
  "Download the Meelu beta for macOS and Windows. It runs crawls and the AI agent on your own computer; expect a security warning on first launch.";

const warnings = [
  {
    platform: "macOS",
    message: "“Meelu” Not Opened. Apple could not verify it is free of malware.",
    steps: [
      "Open the downloaded file and drag Meelu into Applications.",
      "Open Meelu once. When macOS blocks it, click Done.",
      "Go to System Settings → Privacy & Security, scroll down and click Open Anyway next to Meelu.",
      "Confirm with your password. After this, Meelu opens normally.",
    ],
  },
  {
    platform: "Windows",
    message: "Windows protected your PC. Microsoft Defender SmartScreen prevented an unrecognized app from starting.",
    steps: [
      "Run the installer you downloaded.",
      "When the blue SmartScreen window appears, click More info.",
      "Check that the app is Meelu, then click Run anyway.",
    ],
  },
  {
    platform: "Chrome and Edge",
    message: "This file isn't commonly downloaded, or the download is marked as unverified.",
    steps: [
      "Open the browser's downloads list.",
      "Choose Keep (in Chrome, under the ⋮ menu; in Edge, under ⋯ then Show more).",
      "If asked again, confirm that you trust the file.",
    ],
  },
];

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}/download` },
  openGraph: { title, description, url: `${site.url}/download`, type: "website" },
};

export default function DownloadPage() {
  return (
    <div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: softwareApplicationJson }} />
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
            Desktop app · Beta
          </p>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Download Meelu <span className="text-accent">beta</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-sub text-pretty sm:text-lg">
            The desktop app is where the agent works. It runs crawls and the
            agent on your own computer, and connects to your Meelu account.
          </p>
          <div
            role="note"
            className="mx-auto mt-8 flex max-w-2xl items-start gap-3 rounded-2xl border border-warn/40 bg-warn/10 p-5 text-left"
          >
            <TriangleAlert size={20} className="mt-0.5 shrink-0 text-warn" />
            <div className="text-sm text-sub text-pretty">
              <p className="font-medium text-ink">
                This is a beta, and it is not yet verified by Apple, Microsoft or Google.
              </p>
              <p className="mt-2">
                We have not signed the app with Apple or Microsoft yet, and Google has not
                built a reputation for the file. Your browser may warn you when you
                download it, and your computer will warn you the first time you open it.
                This is expected. Meelu is updated continuously, so expect some bugs and rough edges too.{" "}
                <a
                  href="#first-launch"
                  className="text-ink underline decoration-edge underline-offset-4 transition-colors hover:decoration-accent"
                >
                  See how to get past each warning
                </a>
                .
              </p>
            </div>
          </div>
          <div className="mt-10">
            <DownloadButtons />
          </div>
        </div>
      </section>

      <section id="first-launch" className="mx-auto w-full max-w-4xl scroll-mt-20 px-6 py-16">
        <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Security warnings
        </p>
        <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
          What you will see, and how to continue
        </h2>
        <p className="mt-4 max-w-2xl text-base text-sub text-pretty">
          Apple, Microsoft and Google warn about any app they have not verified. Meelu is
          in beta and has not been through their verification yet, so you will see one or
          more of these warnings. Each one appears once. Only download Meelu from this
          page.
        </p>
        <div className="mt-8 grid gap-5 lg:grid-cols-3">
          {warnings.map((warning) => (
            <div key={warning.platform} className="rounded-2xl border border-edge bg-panel p-6">
              <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
                {warning.platform}
              </p>
              <p className="mt-3 text-sm italic text-sub">{warning.message}</p>
              <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm text-sub">
                {warning.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
