import type { Metadata } from "next";
import Link from "next/link";
import {
  CheckCircle2,
  Cpu,
  Gauge,
  Layers,
  ScanText,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { AiContentDetector } from "@/components/ai-detect/detector-tool";
import { MAX_WORDS, MIN_WORDS_TO_JUDGE } from "@/lib/ai-detect/constants";
import { site } from "@/lib/site";

const url = `${site.url}/tools/ai-content-detector`;

const title = "Free AI Content Detector — No Sign-Up, Nothing Uploaded";
const description =
  "Paste a draft or give it a URL and get a paragraph-by-paragraph AI score with the suspect passages quoted back. No account; text never leaves your browser.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "ai content detector",
    "ai content detector tool",
    "ai content detector tools",
    "free ai content detector",
    "ai content detector free",
    "ai content detector online free",
    "free online ai content detector no registration",
    "best ai content detector",
    "best ai content detector 2026",
    "best ai content detector tools 2024",
    "most accurate ai content detector",
    "gptzero ai content detector",
    "zerogpt ai content detector",
    "quillbot ai content detector",
    "writer ai content detector",
    "writers ai content detector tool",
    "writer.com ai content detector",
    "writer.com ai content detector free",
    "sapling ai content detector",
    "smodin ai content detector",
    "ai checker",
    "ai detector url",
    "check a web page for ai content",
    "chatgpt detector",
    "ai writing detector",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const highlights = [
  {
    icon: Cpu,
    title: "Judges the writing, not em dashes",
    body: "It does not count dashes or hunt for banned words. It weighs how the whole passage reads against a large body of writing known to be human and known to be machine-made.",
  },
  {
    icon: ShieldCheck,
    title: "Your text is never uploaded",
    body: "The model runs inside your browser tab. Pasted text is never sent anywhere, nothing is stored and nothing is trained on. Give it a URL and we fetch that public page for you — because a browser cannot — but the scoring still happens on your machine.",
  },
  {
    icon: Layers,
    title: "Tells you which parts look off",
    body: "Each chunk of a few hundred words is scored on its own, so a draft that is half-written and half-generated shows up as mixed instead of being averaged into one bland number.",
  },
  {
    icon: ScanText,
    title: "Points at the actual sentences",
    body: "The paragraphs that scored highest are shown in full, every window opens to the text it scored, and each surface signal lists the exact sentences that made it count — highlighted in place if you want to see them in context.",
  },
  {
    icon: Gauge,
    title: "Tells you when it is unsure",
    body: "Short text, or paragraphs that disagree with each other, lower the confidence shown next to the score. You are told when the answer is shaky instead of getting false certainty.",
  },
  {
    icon: TriangleAlert,
    title: "Says what it gets wrong",
    body: "Plain, formal and academic writing, and English written by non-native speakers, get wrongly flagged. Edited AI text slips through. That is on the page, not in a footnote.",
  },
];

const steps = [
  {
    name: "Paste your text, or a URL",
    text: `Up to ${MAX_WORDS.toLocaleString()} words — an article, an essay, a landing page, a batch of product copy. Paste a web address instead and it fetches the page and strips it to readable text first. Give it at least ${MIN_WORDS_TO_JUDGE} words; below that no detector means anything.`,
  },
  {
    name: "Press check",
    text: "The first check takes a moment while your browser gets set up. After that it is instant, and it keeps working even if you go offline.",
  },
  {
    name: "Read the passages, not just the number",
    text: "You get an overall score, a plain-English verdict, how confident it is, a paragraph-by-paragraph breakdown you can open to read the text behind each score, and every surface signal traced back to the sentences that triggered it. The passages are the useful part.",
  },
];

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "How do AI content detectors work?",
    a: "AI content detectors are classifiers trained on large samples of human-written and machine-generated text, and they score how closely a passage matches the patterns of each. They look at things like how predictable each word is given the words before it, how much sentence length varies, and how often certain phrasings appear. Machine text tends to be smoother and more evenly predictable than human writing, which is the signal most detectors lean on. The output is a probability, not a verdict.",
  },
  {
    q: "How accurate are AI content detectors?",
    a: "Accuracy varies a lot, and no detector is reliable enough to accuse someone on its own. Published evaluations typically report 60% to 90% accuracy depending on the text, the model that wrote it, and how long the sample is. Short passages, technical writing and text by non-native English speakers are where detectors go wrong most often. Treat a high score as a reason to look more closely, never as proof.",
  },
  {
    q: "Can AI detectors be wrong?",
    a: "Yes, in both directions. False positives flag genuine human writing as machine-generated, which happens most with formal, formulaic or plainly written prose, and studies have repeatedly shown non-native English writers are flagged more often. False negatives miss machine text that has been edited, paraphrased or prompted to write in an unusual voice. A detector score is evidence, not a finding, and on a single short paragraph it is weak evidence.",
  },
  {
    q: "Can ChatGPT text be detected?",
    a: "Often, but not dependably. Unedited ChatGPT output has recognisable habits, such as even sentence rhythm, predictable word choice and a preference for balanced structures, and detectors pick those up reasonably well on longer passages. Light editing, a paraphrasing pass or a prompt asking for a specific voice degrades detection sharply. Anyone who wants to avoid detection generally can, which is why detection alone is a weak basis for policy.",
  },
  {
    q: "Does Google penalise AI-generated content?",
    a: "No. Google's stated position is that it rewards helpful, original content regardless of how it was produced, and penalises content made mainly to manipulate rankings. Mass-produced, low-value pages are the problem, not the tool used to write them. AI text that is accurate, useful and genuinely adds something ranks on the same terms as anything else.",
  },
  {
    q: "What percentage of AI content is acceptable?",
    a: "There is no universal number, because it depends on whose rules you are following. Many universities and publishers ask for disclosure rather than setting a threshold, while others allow AI for drafting and research but not for final text. Where a percentage is quoted it is usually a detector score, and detector scores are too noisy to enforce a precise cut-off fairly. Check the specific policy that applies to you rather than aiming at a number.",
  },
  {
    q: "How do teachers check for AI-written work?",
    a: "Most combine a detector score with context: the student's previous writing, the assignment's specific requirements, version history in the document, and a conversation about how the work was produced. Detectors alone are widely considered insufficient, and several institutions have turned them off after false positives. Version history and drafts tend to be more convincing than any score. The usual practice is to treat a flag as the start of a conversation.",
  },
  {
    q: "Is there a free AI content detector?",
    a: "Yes, several, including this one, which runs a trained classifier in your browser with no account needed. Free detectors are generally as accurate as paid ones, because they use similar techniques and the limits are in the method rather than the price. Whatever you use, check more than one passage and read the writing yourself before drawing any conclusion.",
  },
];

export default function AiContentDetectorPage() {
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
        <div className="relative mx-auto w-full max-w-3xl px-6 py-16 sm:py-20">
          <nav aria-label="Breadcrumb" className="font-mono text-xs text-faint">
            <Link href="/tools" className="transition-colors hover:text-accent">
              Free tools
            </Link>
            <span className="px-1.5">/</span>
            <span>AI content detector</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free AI content detector
          </h1>
          <p className="mt-4 text-base text-sub text-pretty sm:text-lg">
            Something about this draft reads like ChatGPT wrote it. Paste it in and find
            out which paragraphs look machine-made, with the suspect passages quoted back
            so you can judge them yourself. Paste a web address instead and it reads the
            page for you. No account, and pasted text never leaves your browser. No
            detector can prove anything, so treat a high score as a reason to look closer
            — never as evidence.
          </p>

          <div className="mt-8">
            <AiContentDetector />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Text or page URL",
              "Pasted text stays local",
              "Per-paragraph scores",
              `${MIN_WORDS_TO_JUDGE}+ words`,
              "Works offline after first run",
            ].map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <CheckCircle2 size={12} className="text-good" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto w-full max-w-5xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          What this AI content detector tool does
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {highlights.map(({ icon: Icon, title: heading, body }) => (
            <article key={heading} className="rounded-2xl border border-edge bg-panel p-5">
              <Icon size={18} className="text-accent" />
              <h3 className="mt-3 text-base font-medium text-ink">{heading}</h3>
              <p className="mt-2 text-sm leading-relaxed text-sub">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-5xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            How to check if text was written by AI
          </h2>
          <ol className="mt-8 grid gap-5 sm:grid-cols-3">
            {steps.map((step, i) => (
              <li key={step.name} className="rounded-2xl border border-edge bg-panel p-5">
                <span className="font-mono text-xs text-faint">Step {i + 1}</span>
                <h3 className="mt-2 text-base font-medium text-ink">{step.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-sub">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Compared with GPTZero, ZeroGPT, Originality and the rest
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-sub">
            Honest version: the paid tools do more than this one. Here is the split, so
            you can pick the right thing rather than the thing that ranked.
          </p>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="text-base font-medium text-ink">
                What they do that this does not
              </h3>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-sub">
                <li>
                  <strong className="font-medium text-ink">Plagiarism databases.</strong>{" "}
                  Originality.ai and Turnitin check text against an index of existing
                  work. This has no database and never will.
                </li>
                <li>
                  <strong className="font-medium text-ink">Bulk and API.</strong> Scanning
                  a thousand URLs or wiring detection into a CMS is what the paid tiers at
                  Originality and GPTZero are for.
                </li>
                <li>
                  <strong className="font-medium text-ink">Team accounts and audit
                  trails.</strong> Saved reports, shared seats, per-writer history. An
                  institution buying Turnitin is buying the record-keeping.
                </li>
                <li>
                  <strong className="font-medium text-ink">Extras around the edges.</strong>{" "}
                  The Writer.com AI content detector sits inside a whole writing platform;
                  the Quillbot AI content detector sits next to a paraphraser; Sapling and
                  Smodin bundle theirs with grammar and summarising tools.
                </li>
              </ul>
            </div>

            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="text-base font-medium text-ink">
                What this does that they do not
              </h3>
              <ul className="mt-3 space-y-2 text-sm leading-relaxed text-sub">
                <li>
                  <strong className="font-medium text-ink">Never sees your text.</strong>{" "}
                  GPTZero, ZeroGPT, Sapling, Smodin, Writer and Quillbot all need you to
                  upload the thing you are suspicious about. This checks it in your own
                  browser instead.
                </li>
                <li>
                  <strong className="font-medium text-ink">Free with no registration.</strong>{" "}
                  No account, no email wall at 300 words, no credits. There is no server
                  bill to recoup.
                </li>
                <li>
                  <strong className="font-medium text-ink">Shows its working.</strong> A
                  paragraph-by-paragraph breakdown you can open to read the text behind
                  each score, the flagged passages quoted in full, and every surface
                  signal traced to the sentences that triggered it — so you can see
                  whether it reacted to who wrote the text or just to a formal paragraph.
                </li>
                <li>
                  <strong className="font-medium text-ink">Admits what it gets wrong.</strong>{" "}
                  The cases where it misfires are on this page, next to the result, rather
                  than an accuracy claim in a marketing headline.
                </li>
              </ul>
            </div>
          </div>

          <p className="mt-6 text-sm leading-relaxed text-sub">
            If you need a plagiarism database or bulk scanning, buy one of them. If you
            want to check a draft without handing it to a third party, this is the
            better-shaped tool.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          What it does not do
        </h2>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not prove anything.</strong> No
            detector can show that a person did or did not write something, and this one
            gets it wrong often enough to matter. Treat a high score as a reason to look
            closer, never as a finding.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not catch edited AI text.</strong>{" "}
            Paraphrased, humanised or half-rewritten output slips through, and that is the
            text most people actually want caught.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not name the model.</strong> No tool
            can reliably tell you whether ChatGPT, Claude or Gemini wrote a passage,
            whatever the marketing says.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not check plagiarism.</strong> There
            is no database of existing work behind this. For overlap between two documents
            you have, use the{" "}
            <Link
              href="/tools/similarity-checker"
              className="font-medium text-accent hover:text-accent-hi"
            >
              similarity checker
            </Link>
            .
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not do bulk.</strong> One text at a
            time, up to {MAX_WORDS.toLocaleString()} words. No crawling, no CSV, no
            queue.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It does not store results.</strong> Nothing is
            saved, so there is no history and no shareable report. Reload the page and it
            is gone.
          </li>
        </ul>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Frequently asked questions
          </h2>
          <div className="mt-8 flex flex-col gap-3">
            {faqs.map((faq) => (
              <details key={faq.q} className="group rounded-2xl border border-edge bg-panel p-5">
                <summary className="cursor-pointer list-none text-base font-medium text-ink marker:hidden">
                  {faq.q}
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-sub">{faq.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          The rest of the free tools
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          If you are checking content you commissioned, the{" "}
          <Link
            href="/tools/similarity-checker"
            className="font-medium text-accent hover:text-accent-hi"
          >
            similarity checker
          </Link>{" "}
          is the other half of the job — it finds passages two documents share, which
          catches the copy-paste that a detector like this one cannot. The{" "}
          <Link
            href="/tools/seo-audit"
            className="font-medium text-accent hover:text-accent-hi"
          >
            SEO audit
          </Link>{" "}
          and the{" "}
          <Link
            href="/tools/broken-link-checker"
            className="font-medium text-accent hover:text-accent-hi"
          >
            broken link checker
          </Link>{" "}
          crawl a whole site for the technical problems that cost you more traffic than
          any of this.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          All of them are pieces of{" "}
          <Link href="/" className="font-medium text-accent hover:text-accent-hi">
            Meelu
          </Link>
          , a desktop app where an AI marketing agent suggests what to do with your site and you decide.{" "}
          <Link href="/download" className="font-medium text-accent hover:text-accent-hi">
            Download the app
          </Link>
          .
        </p>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "Meelu Free AI Content Detector",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Scores in the browser — pasted text is never uploaded",
                "Checks a pasted page URL by fetching and stripping the page for you",
                "An overall AI score with a plain-English verdict",
                "A paragraph-by-paragraph breakdown of the same text",
                "The most suspect passages quoted back in full",
                "Every scored window opens to show the text behind its score",
                "Surface signals traced to the exact sentences that triggered them",
                "Tells you when the text is too short or too mixed to be confident",
                "States where it misfires, including academic and non-native English writing",
                `Up to ${MAX_WORDS.toLocaleString()} words per check, no registration`,
              ],
              publisher: { "@type": "Organization", name: site.name, url: site.url },
            },
            {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: faqs.map((faq) => ({
                "@type": "Question",
                name: faq.q,
                acceptedAnswer: { "@type": "Answer", text: faq.a },
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "HowTo",
              name: "How to check if text was written by AI",
              description:
                "Paste the text or a page URL, let it score each paragraph in your browser, and read the flagged passages rather than the headline percentage.",
              step: steps.map((step, i) => ({
                "@type": "HowToStep",
                position: i + 1,
                name: step.name,
                text: step.text,
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "BreadcrumbList",
              itemListElement: [
                {
                  "@type": "ListItem",
                  position: 1,
                  name: "Free tools",
                  item: `${site.url}/tools`,
                },
                {
                  "@type": "ListItem",
                  position: 2,
                  name: "AI content detector",
                  item: url,
                },
              ],
            },
          ]),
        }}
      />
    </div>
  );
}
