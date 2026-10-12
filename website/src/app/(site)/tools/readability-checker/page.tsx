import type { Metadata } from "next";
import Link from "next/link";
import {
  BookOpen,
  CheckCircle2,
  Clipboard,
  Gauge,
  Highlighter,
  Link2,
  Lock,
  Sigma,
} from "lucide-react";
import { ReadabilityChecker } from "@/components/readability/checker-tool";
import { MAX_WORDS } from "@/lib/readability/analyse";
import { FLESCH_BANDS } from "@/lib/readability/scores";
import { site } from "@/lib/site";

const url = `${site.url}/tools/readability-checker`;

const title = "Free Readability Checker — Paste Text or Check a URL";
const description =
  "Paste text or give it a URL for a Flesch Reading Ease score, a grade level, and the exact sentences making it hard work. Free, no sign-up, text stays local.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "readability checker",
    "free readability checker",
    "readability checker free",
    "best readability checker",
    "hemingway readability checker",
    "readability checker grade level",
    "color readability checker",
    "text readability checker",
    "readability checker online",
    "readability checker url",
    "check readability of a web page",
    "website readability checker",
    "readability checker accurate",
    "flesch reading ease calculator",
    "flesch kincaid grade level",
    "gunning fog index calculator",
    "smog index",
    "coleman liau index",
    "passive voice checker",
    "reading level checker",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is readability?",
    a: "Readability is how easy a piece of text is to read and understand. In practice it is measured with formulas that look at two things: how long your sentences are and how long your words are. Those two inputs predict comprehension surprisingly well, which is why plain-language guidance for government, health and legal writing is built on them. Readability says nothing about whether the ideas are good — only about how much work the reader has to do to get at them.",
  },
  {
    q: "How do you calculate readability?",
    a: "Every common readability formula combines average sentence length with a measure of word difficulty. Flesch Reading Ease is 206.835 minus 1.015 times words per sentence minus 84.6 times syllables per word. Flesch-Kincaid grade level is 0.39 times words per sentence plus 11.8 times syllables per word minus 15.59. Gunning Fog uses the share of words with three or more syllables instead, and Coleman-Liau and ARI use characters per word so they need no syllable counting at all.",
  },
  {
    q: "What is a good Flesch reading ease score?",
    a: "Aim for 60 to 70 for a general audience — that band is defined as plain English and is what most US adults read comfortably. Above 80 is very easy, the level of a tabloid or a children's book. Between 50 and 60 is fairly difficult and suits an informed or trade readership. Below 30 is the territory of academic papers, contracts and insurance policies, where most readers have to reread sentences to follow them.",
  },
  {
    q: "What reading level should you write for?",
    a: "Grade 8 to 9 for anything aimed at the general public. That is the average adult reading level in the US and UK, and health, government and plain-language standards usually ask for grade 8 or lower. Public health information is often held to grade 6. Technical and trade writing sits higher and that is fine, as long as it matches the people actually reading it. Writing below your audience's level costs nothing; writing above it loses readers.",
  },
  {
    q: "What is the Flesch-Kincaid grade level?",
    a: "Flesch-Kincaid grade level converts a text's difficulty into a US school year, so a score of 8 means an average eighth-grader, around thirteen years old, could read it once and follow it. It uses the same two inputs as Flesch Reading Ease — words per sentence and syllables per word — but scales them so the output is a year rather than a 0 to 100 score. It was developed for the US Navy in 1975 to grade training manuals, and it is the figure most style guides and word processors report.",
  },
  {
    q: "What is the Gunning Fog index?",
    a: "The Gunning Fog index estimates the years of formal education a reader needs to understand a passage on the first reading. It is 0.4 multiplied by the sum of average sentence length and the percentage of complex words, where complex means three or more syllables, excluding proper nouns, familiar compounds and verb endings such as -ed and -es. A Fog score of 8 is easy reading for most people; business writing commonly lands around 11 to 14, and anything above 17 reads as academic.",
  },
  {
    q: "How do you improve readability?",
    a: "Cut the long sentences first. Sentence length is the heavier input in every formula, so splitting a 40-word sentence in two moves the score more than any word-swapping. Then replace Latinate words with short ones: utilise becomes use, facilitate becomes help, in order to becomes to. Put the main clause first, use active verbs, and drop the adverbs that are doing no work. Aim for an average of 15 to 20 words per sentence with real variation between them.",
  },
  {
    q: "Does readability affect SEO?",
    a: "Not directly. Google has no readability score in its ranking systems and has said so repeatedly. What readability changes is whether people finish the page, whether they come back, and whether anyone links to it — and those do feed the signals search engines can measure. It matters more now that answer engines quote pages: a short, plainly worded sentence is far easier for a model to lift as a citation than a 45-word one with three subordinate clauses.",
  },
];

const highlights = [
  {
    icon: Gauge,
    title: "Flesch Reading Ease, on a banded gauge",
    body: "The 0 to 100 score with Flesch's own bands drawn to scale, so you can see whether you are sitting in plain English or three bands above it.",
  },
  {
    icon: BookOpen,
    title: "Grade level with a real audience",
    body: "Not just a number. Every grade comes with who reads at it, so 8th grade reads as most US adults read comfortably here rather than as a score to chase.",
  },
  {
    icon: Sigma,
    title: "The scores your style guide asks for",
    body: "Flesch Reading Ease, Flesch-Kincaid, ARI, Gunning Fog, SMOG and Coleman-Liau — so when a client or a plain-language standard names a target, you have the number.",
  },
  {
    icon: Highlighter,
    title: "The sentences causing the score",
    body: "Long sentences, sentences stacked with three-syllable words, passive constructions and adverbs — each listed, and clickable to see it in its paragraph.",
  },
  {
    icon: Lock,
    title: "Pasted text never leaves the browser",
    body: "Paste and nothing is sent anywhere: the analysis is JavaScript running in your tab, so an unpublished draft stays unpublished. Give it a URL and the only thing our server does is fetch that page and hand back its text — the scoring still happens in your tab, and nothing is stored either way.",
  },
  {
    icon: Link2,
    title: "Score a live page by URL",
    body: "Give it an address and the page is fetched once, stripped of navigation, headers, footers and scripts, then scored as a whole and passage by passage — every paragraph, heading and list item, hardest first.",
  },
  {
    icon: Clipboard,
    title: "Copy the report or export it",
    body: "A plain-text report for the clipboard, a sentence-level CSV you can sort by word count, and a scores CSV with every formula and its working.",
  },
];

const steps = [
  {
    name: "Paste the text, or give it a URL",
    text: `Paste an article, landing page, email or product description — up to ${MAX_WORDS.toLocaleString()} words, scored as you type with nothing uploaded. Or switch to the URL box and we fetch the page once, throw away the navigation, header, footer and scripts, and score the article that is left.`,
  },
  {
    name: "Read the grade, then the passages",
    text: "The headline number tells you where the page sits. Below it, every sentence is listed with what is wrong with it — and a URL also gets each paragraph, heading and list item scored on its own, hardest first, so you can see which passages drag the page down.",
  },
  {
    name: "Edit in place and watch it move",
    text: "Split a long sentence, swap a Latinate word, and the pasted-text score updates on the next keystroke. Re-run the URL once the page is published to check the fix landed.",
  },
];

export default function ReadabilityCheckerPage() {
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
            <span>Readability checker</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free readability checker
          </h1>
          <p className="mt-4 text-base text-sub text-pretty sm:text-lg">
            Your writing makes sense to you. The question is whether it makes sense
            on first read to everyone else. Paste your text, or give it the address
            of a page, and you get a reading score, the school grade it is pitched
            at, and the exact sentences that are hard work — a URL scored paragraph
            by paragraph, hardest first. Pasted text never leaves your browser. No
            account, nothing stored.
          </p>

          <div className="mt-8">
            <ReadabilityChecker />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Text or URL",
              "Passage by passage",
              "Six formulas",
              `${MAX_WORDS.toLocaleString()} words`,
              "Copy or export",
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
          What the text readability checker measures
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
            How to check the readability of your writing
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

      <section>
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            What the readability checker grade level means
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-sub">
            A grade level is a US school year, and every band below is Flesch&rsquo;s
            own. The average US adult reads at about eighth or ninth grade, and a
            quarter of them read below sixth. Writing at grade 14 does not make you
            sound expert; it makes three readers in four work harder than they will.
          </p>
          <div className="mt-6 overflow-x-auto rounded-2xl border border-edge bg-panel">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                  <th className="px-5 py-3 font-medium">Flesch score</th>
                  <th className="px-5 py-3 font-medium">Reads like</th>
                  <th className="px-5 py-3 font-medium">Grade level</th>
                  <th className="px-5 py-3 font-medium">Who that is</th>
                </tr>
              </thead>
              <tbody>
                {FLESCH_BANDS.map((band, i) => (
                  <tr key={band.label} className="border-b border-edge/60 align-top">
                    <td className="px-5 py-3 font-mono text-xs text-ink whitespace-nowrap">
                      {i === 0
                        ? "90 to 100"
                        : band.min === Number.NEGATIVE_INFINITY
                          ? "Below 10"
                          : `${band.min} to ${FLESCH_BANDS[i - 1].min}`}
                    </td>
                    <td className="px-5 py-3 text-sm text-ink">{band.label}</td>
                    <td className="px-5 py-3 text-sm text-sub">{band.school}</td>
                    <td className="px-5 py-3 text-xs leading-relaxed text-sub">
                      {band.audience}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-4 text-xs leading-relaxed text-faint">
            The bottom band has no lower bound. Flesch scores can go negative, and
            insurance policies routinely do.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          How accurate is a readability checker, really
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          Accurate enough to act on, and worth knowing where it stops. A readability
          score looks at two things: how long your sentences are and how long your
          words are. That predicts how much effort reading takes, and it is why
          plain-language rules for government, health and legal writing are built on
          it.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          What it cannot see is whether the writing is any good. It does not know if
          an argument holds together, if a joke lands, or if a short sentence is
          nonsense. A page of unrelated three-word sentences would score top marks.
          Treat the score as a way to catch sentences that ran away from you, not as
          a grade for the writing.
        </p>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Looking for a colour readability checker?
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            Then you probably want a different tool, and it is more useful to say so
            than to fudge it. People searching for a color readability checker
            usually mean colour contrast: whether grey text on a cream background is
            legible, not what grade the sentences are written at. That is measured as
            a WCAG contrast ratio between two colours and has nothing to do with
            syllables.
          </p>
          <ul className="mt-5 space-y-3 text-sm leading-relaxed text-ink/90">
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">The numbers to hit.</strong> 4.5:1 for
              body text and 3:1 for large text — 18px bold or 24px regular and above
              — to meet WCAG 2.2 level AA. Level AAA asks for 7:1 and 4.5:1.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Where to check it.</strong> The WebAIM
              contrast checker for two hex values, the contrast line in the Chrome or
              Firefox element inspector for a live page, or the accessibility panel in
              Figma. All free, all take seconds.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Both matter, separately.</strong> A page
              can be written at sixth-grade level and still be unreadable in 12px
              light grey. Contrast is a rendering problem; the tool on this page is a
              writing one.
            </li>
          </ul>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          Compared with the Hemingway readability checker
        </h2>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          Hemingway is the tool most people mean when they search for a readability
          checker, and it is good at what it does. It highlights as you draft, grades
          each sentence in place, and gives you one grade number to aim at. If you
          write inside the editor, that is the right workflow and this page is not
          trying to take it from you.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          The differences are worth knowing before you pick. Hemingway gives one
          grade; this gives you all six of the scores a client or style guide might
          name, so you are never stuck without the one you were asked for. It also
          takes a URL, which Hemingway does not. Hemingway sells a desktop app; this
          is free online with no upsell. Hemingway is a place to draft; this is a
          place to measure. Plenty of people should use both, in that order.
        </p>
        <p className="mt-4 text-sm leading-relaxed text-sub">
          One thing this does that in-editor checkers generally do not: pasted text
          is scored in your own browser and never sent anywhere. If you are checking
          an unpublished announcement, a client draft or anything under embargo, that
          difference is not a small one.
        </p>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            What it does not do
          </h2>
          <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">English only.</strong> Every formula
              here was fitted to English, and so are the syllable rules, the passive
              patterns and the adverb test. Other languages will produce a number that
              means nothing.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">
                It measures structure, not clarity.
              </strong>{" "}
              Sentence length and word length are the whole input. Confused thinking
              in short sentences scores well, and that is a limit of the method rather
              than a bug in the tool.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">
                Passive detection is a pattern match.
              </strong>{" "}
              A form of to be followed by a past participle catches most passives and
              also catches was tired and is interested, which are not passive at all.
              Read each flagged phrase rather than deleting on sight.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No grammar or spelling check.</strong>{" "}
              No tone scoring, no sentiment analysis, no AI rewriting. It measures how
              hard your writing is to read, and stops there.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Nothing is saved.</strong> No account, no
              history between visits, no result link to share. Copy or download the
              report if you want to keep it.
            </li>
          </ul>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
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
      </section>

      <section className="border-t border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Readable is one of several things a page has to be
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            It also has to be crawlable, indexable and free of dead ends. The{" "}
            <Link
              href="/tools/seo-audit"
              className="font-medium text-accent hover:text-accent-hi"
            >
              free SEO audit tool
            </Link>{" "}
            checks titles, canonicals, redirects, schema and AI crawler access across
            your site, and the{" "}
            <Link
              href="/tools/broken-link-checker"
              className="font-medium text-accent hover:text-accent-hi"
            >
              broken link checker
            </Link>{" "}
            finds the 404s readers hit halfway down the page you just made readable.
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
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "Meelu Free Readability Checker",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Flesch Reading Ease score on a banded 0-100 gauge",
                "Flesch-Kincaid grade level with the audience it corresponds to",
                "Automated Readability Index, Gunning Fog, SMOG and Coleman-Liau",
                "Scores a live page by URL, paragraph by paragraph, hardest first",
                "Word, sentence, paragraph, syllable and character counts",
                "Long sentences, complex words, passive voice and adverbs listed by sentence",
                "Recommendations linked to the sentences that caused them",
                "Runs entirely in the browser with no upload",
                "Copy report, text export and CSV export",
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
              name: "How to check the readability of a piece of writing",
              description:
                "Paste text into a readability checker, read the Flesch score and grade level, then edit the sentences that caused it.",
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
                  name: "Readability checker",
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
