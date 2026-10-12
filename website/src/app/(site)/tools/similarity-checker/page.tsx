import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowLeftRight,
  CheckCircle2,
  Download,
  Fingerprint,
  Quote,
  ShieldCheck,
  SplitSquareHorizontal,
} from "lucide-react";
import { SimilarityChecker } from "@/components/similarity/checker-tool";
import { MAX_WORDS } from "@/lib/similarity/compare";
import { site } from "@/lib/site";

const url = `${site.url}/tools/similarity-checker`;

const cap = MAX_WORDS.toLocaleString();

const title = "Free Similarity Checker — Compare Two Texts or URLs";
const description =
  "Paste two texts or two URLs and see how much they share: a percentage, the matching sentences, and word-for-word passages. In your browser, no sign-up.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "similarity checker",
    "free similarity checker",
    "similarity checker free",
    "online similarity checker",
    "text similarity checker",
    "document similarity checker",
    "similarity checker between two texts",
    "ai similarity checker",
    "ai similarity checker free",
    "free ai similarity checker",
    "turnitin similarity checker",
    "turnitin similarity checker free",
    "similarity checker turnitin",
    "essay similarity checker",
    "paper similarity checker",
    "word similarity checker",
    "wgu similarity checker",
    "code similarity checker",
    "face similarity checker",
    "face similarity checker online free",
    "duplicate content checker",
    "plagiarism checker",
    "compare two documents",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is text similarity?",
    a: "Text similarity is a measure of how much two pieces of writing have in common, usually given as a percentage. Lexical similarity counts shared words and phrases, so it catches copying. Semantic similarity compares meaning, so it catches the same idea written differently. Most checkers report the lexical figure, because it is the one you can point at and verify.",
  },
  {
    q: "What is duplicate content?",
    a: "Duplicate content is the same or near-identical text appearing at more than one address, either within a site or across sites. It happens most often by accident: printer-friendly pages, URL parameters, filtered category listings, product descriptions copied from a supplier, or the same article republished under two paths. It is a housekeeping problem rather than a moral one, but it costs traffic all the same.",
  },
  {
    q: "How much similarity is acceptable?",
    a: "There is no universal figure, and any tool that gives you one is guessing. Academic institutions typically accept somewhere between 10% and 25% including quotations and references, and set their own bar. For two pages on the same website, anything above about 60% means one of them should be merged or canonicalised. Read the matched passages rather than the headline number: 40% made of properly cited quotes is fine, 10% made of one lifted paragraph is not.",
  },
  {
    q: "What is semantic similarity?",
    a: "Semantic similarity measures whether two texts mean the same thing, regardless of the words used. \"Cut costs\" and \"reduced expenditure\" share no wording but carry the same claim, and a semantic comparison scores that as a match. It is normally computed by turning each text into a vector with a language model and measuring the angle between them. Lexical methods cannot do this, which is why heavy paraphrasing slips past them.",
  },
  {
    q: "How is text similarity calculated?",
    a: "The common method breaks both texts into overlapping runs of words, called shingles, and counts how many runs they share. A second pass pairs each sentence with its closest match on the other side and scores the pair on shared vocabulary, usually with TF-IDF weighting and cosine similarity so that common words count for less. The two numbers answer different questions: verbatim overlap and reworded overlap.",
  },
  {
    q: "Can paraphrasing be detected?",
    a: "Light paraphrasing, yes. Swapping a few words, reordering a clause or changing the tense leaves enough shared vocabulary for a sentence to still register as a match. A genuine rewrite in different words will not be caught by any method that compares wording alone, because there is nothing left to compare. Detecting that needs a semantic model, and even then the result is a judgement rather than proof.",
  },
  {
    q: "What is the difference between plagiarism and duplicate content?",
    a: "Plagiarism is using someone else's work without credit, which is an academic and ethical question. Duplicate content is the same text existing at two addresses, which is a technical and SEO question. Self-duplication is common and is not plagiarism. A checker can measure overlap; only a person can decide whether that overlap was dishonest.",
  },
  {
    q: "Does duplicate content hurt SEO?",
    a: "Not as a penalty. Search engines filter rather than punish: when two pages say the same thing, one is chosen for the results and the other is dropped, so the duplicate quietly stops earning traffic. The real costs are crawl budget spent on pages that will never rank and link signal split between two URLs that should have been one. The fix is a canonical tag, a redirect or a merge.",
  },
];

const highlights = [
  {
    icon: ArrowLeftRight,
    title: "Both directions, not one average",
    body: "How much of A appears in B is a different number from how much of B appears in A, and the gap is the whole story when one text is longer. Both are reported in plain words.",
  },
  {
    icon: SplitSquareHorizontal,
    title: "Shows you the sentences that match",
    body: "Every sentence is paired with its closest match on the other side, so you can read the overlap for yourself instead of arguing with a percentage.",
  },
  {
    icon: Quote,
    title: "Longest shared passages",
    body: "The longest runs of identical words the two texts share, with a word count on each. A forty-word identical run is more convincing evidence than any percentage.",
  },
  {
    icon: Fingerprint,
    title: "What is only in yours",
    body: "The sentences with nothing close to them on the other side — the part that is genuinely original, listed so you can see what survived.",
  },
  {
    icon: ShieldCheck,
    title: "Pasted text never leaves the browser",
    body: "The comparison is JavaScript running on your machine. Nothing is uploaded, nothing is stored and nothing is added to anybody's archive of submitted work.",
  },
  {
    icon: Download,
    title: "CSV export, no sign-up",
    body: "Every matched pair with its score, ready for Excel, Sheets or Numbers — so an editor can work down the list without opening the tool.",
  },
];

const steps = [
  {
    name: "Put a text in each box",
    text: "Paste the writing itself, or paste a URL and the page is fetched and reduced to its readable text. One side can be text and the other a URL.",
  },
  {
    name: "Press compare",
    text: "The whole comparison happens on your own machine, in under a second. Nothing is uploaded and nothing is kept.",
  },
  {
    name: "Read the matches, not just the number",
    text: "Shaded sentences in the side-by-side view jump to their partner when clicked. Work down the matched pairs, then export the list to CSV.",
  },
];

export default function SimilarityCheckerPage() {
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
        <div className="relative mx-auto w-full max-w-5xl px-6 py-16 sm:py-20">
          <nav aria-label="Breadcrumb" className="font-mono text-xs text-faint">
            <Link href="/tools" className="transition-colors hover:text-accent">
              Free tools
            </Link>
            <span className="px-1.5">/</span>
            <span>Similarity checker</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free similarity checker
          </h1>
          <p className="mt-4 max-w-3xl text-base text-sub text-pretty sm:text-lg">
            You have two pieces of writing and you need to know how much of one is in
            the other. Paste a text into each box — or a web address, and the page is
            fetched for you — and get a percentage, the sentences that match, and the
            passages the two share word for word. Nothing is uploaded. No sign-up.
          </p>

          <div className="mt-8">
            <SimilarityChecker />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Nothing uploaded",
              "Both directions, not an average",
              "Matched sentences listed",
              "CSV export",
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
          What this document similarity checker reports
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
            How to check similarity between two texts
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

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          What each number means
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-sub">
          Most free similarity checkers give you one percentage and no way to argue with it.
          These are the five figures this one reports and what each is actually measuring.
        </p>
        <dl className="mt-6 space-y-3">
          {[
            {
              term: "Overall similarity",
              tone: "text-ink",
              body: "The higher of the two directions below. Under 30% the two texts are original with respect to each other; 30–60% is partly duplicated and worth reading through; over 60% means one document is largely the other one.",
            },
            {
              term: "How much of A appears in B",
              tone: "text-accent",
              body: "Containment, one way round. If this is high and the other is low, a short text has been copied into a long one — which is the case a single averaged score hides completely.",
            },
            {
              term: "Word-for-word overlap",
              tone: "text-bad",
              body: "How much of this text appears in the other completely untouched. This is the number to quote when the question is whether something was copied rather than written.",
            },
            {
              term: "Matched-sentence coverage",
              tone: "text-warn",
              body: "How much of the text sits in a sentence that has a close partner on the other side. Higher than the word-for-word figure when copying has been lightly tidied up.",
            },
            {
              term: "Longest shared passage",
              tone: "text-good",
              body: "The longest unbroken run of identical words the two share. Short runs are ignored, because a handful of words in common is just how English works.",
            },
          ].map((row) => (
            <div key={row.term} className="rounded-xl border border-edge bg-panel p-4">
              <dt className={`text-sm font-medium ${row.tone}`}>{row.term}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-sub">{row.body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Duplicate content and plagiarism are not the same problem
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            The same percentage answers two different questions depending on who is asking, and
            the searches that land on a similarity checker come from both.
          </p>
          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="text-base font-medium text-ink">Duplicate content is an SEO problem</h3>
              <p className="mt-2 text-sm leading-relaxed text-sub">
                Two of your own pages saying the same thing. Nobody has done anything wrong;
                the pages are just competing. Google picks one and filters the other out of the
                results, so the duplicate quietly stops earning traffic. The fix is a canonical
                tag, a redirect or a merge — not a rewrite. Most of it is created by templates
                and URL parameters rather than by writers.
              </p>
            </div>
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="text-base font-medium text-ink">Plagiarism is an authorship problem</h3>
              <p className="mt-2 text-sm leading-relaxed text-sub">
                Somebody else&rsquo;s words presented as yours. Here the percentage matters far
                less than the passages: one uncited paragraph is serious at 4% overall, and a
                page of properly quoted and referenced material is fine at 40%. Read the matched
                sentences and the longest shared runs, and ignore the headline.
              </p>
            </div>
          </div>
          <p className="mt-6 text-sm leading-relaxed text-sub">
            This tool measures the overlap. Which of the two problems you have is your call, and
            it changes what you do about it.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          If you came here looking for Turnitin
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          A lot of people searching for a Turnitin similarity checker — or a Turnitin similarity
          checker free of charge — want the Turnitin similarity report without paying for
          Turnitin. That is not something any free tool can give you, and the sites promising it
          are either selling something else or keeping your paper. Here is the honest version.
        </p>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">Turnitin&rsquo;s number comes from its archive.</strong>{" "}
            Your paper is matched against tens of millions of student submissions, licensed
            publisher content and a web crawl. The archive is the product. Nobody else has it,
            so nobody else can reproduce the number.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">This compares two documents you supply.</strong> If
            you already know the source you worked from — lecture notes, a shared draft, an
            earlier version of your own assignment, a classmate&rsquo;s essay you both built
            from the same outline — this will show you exactly how much of it survived into your
            draft, sentence by sentence.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">
              When that is enough, and when it is not.
            </strong>{" "}
            Enough: checking your own rewrite actually reads as a rewrite, or settling an
            argument about two documents in front of you. Not enough: predicting a submission
            score, or finding out whether a passage exists somewhere on the internet. For the
            second one you need a service with an index, and you should expect to pay for it.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">Your institution already has the report.</strong>{" "}
            Most universities let you see the similarity report on a draft submission before the
            final one. That report is the only one that counts, and it is free to you. If you
            searched for a similarity checker Turnitin would agree with, that draft submission is
            it — no third-party number, this one included, predicts the score.
          </li>
        </ul>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            If you came here looking for an AI similarity checker
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            &ldquo;AI similarity checker&rdquo; gets searched for two different things, and the
            free AI similarity checker results that come back rarely say which one they are. This
            is an AI similarity checker free of any model at all, so it is worth being specific.
          </p>
          <div className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
            <div className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">If you mean a checker that uses AI:</strong> this
              one does not, on purpose. For measuring how much two documents share, the old
              methods win on the things that matter here — the same texts always give the same
              number, it runs instantly on your own machine, and there is no company to send
              your draft to. What you give up is spotting a passage rewritten in different
              words. That is the trade, said plainly rather than hidden behind an AI-powered
              badge.
            </div>
            <div className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">
                If you mean a checker for AI-written text:
              </strong>{" "}
              that is a different question — not how similar two texts are, but whether one of
              them came out of a model. Use the{" "}
              <Link
                href="/tools/ai-content-detector"
                className="font-medium text-accent hover:text-accent-hi"
              >
                free AI content detector
              </Link>{" "}
              instead. It is the wrong tool for duplicate content and this is the wrong tool for
              detecting a model, and running the pair of them answers both.
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          What it does not do
        </h2>
        <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">No database, no web search.</strong> It compares the
            two documents you give it. It cannot tell you whether a sentence appears anywhere
            else, because there is no index behind it to look in.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">It compares wording, not meaning.</strong> A passage
            genuinely rewritten in different words scores near zero, so a careful rewrite can
            still slip past. No checker that reads wording can honestly claim otherwise.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">Not a code similarity checker.</strong> It finds
            identical runs in source files, but a copy with everything renamed slips past. Use a
            purpose-built one for that.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">Not a face similarity checker.</strong> This
            compares writing. If you are after a face similarity checker online free, you want
            an image tool — there is no upload here and nothing that looks at photographs.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">No file upload.</strong> Word documents, PDFs and
            Google Docs need their text copied in. Nothing is parsed, and nothing is kept.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">Built for English.</strong> Other languages written
            in the same alphabet mostly work. Languages that do not put spaces between words
            will give wrong numbers.
          </li>
          <li className="rounded-xl border border-edge bg-panel p-4">
            <strong className="font-medium">
              {cap} words a side.
            </strong>{" "}
            Longer texts are cut and the report tells you it happened. Compare them in sections
            rather than trusting a truncated score.
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
          Duplication is rarely the only thing wrong
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          If two of your own pages came back heavily similar, the next questions are which one
          Google has picked, whether the canonical tags agree with you and how many other pages
          are in the same state. The{" "}
          <Link
            href="/tools/seo-audit"
            className="font-medium text-accent hover:text-accent-hi"
          >
            free SEO audit tool
          </Link>{" "}
          crawls the site and answers all three, including duplicate titles and descriptions
          across every page it reads. The{" "}
          <Link
            href="/tools/broken-link-checker"
            className="font-medium text-accent hover:text-accent-hi"
          >
            broken link checker
          </Link>{" "}
          covers the other half of a content clean-up: the links that stopped working while
          nobody was looking.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          All three are pieces of{" "}
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
              name: "Meelu Free Similarity Checker",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Compares two pasted texts or two URLs for duplicate content",
                "Overall similarity score with plain guidance on what the number means",
                "Reported in both directions, not a single average",
                "Word-for-word overlap, so you can say whether something was copied",
                "Every matching sentence paired up and listed",
                "The longest passages the two share word for word",
                "The sentences that are only in one of them",
                "Side-by-side view with matched passages highlighted and scroll-synced",
                "CSV export of every matched sentence pair",
                "Runs in the browser: pasted text is never uploaded",
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
              name: "How to check the similarity between two texts",
              description: `Paste two texts or two URLs, compare them, and read the matched sentences and shared passages rather than only the percentage.`,
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
                  name: "Similarity checker",
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
