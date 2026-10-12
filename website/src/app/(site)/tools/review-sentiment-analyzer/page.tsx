import type { Metadata } from "next";
import Link from "next/link";
import {
  CheckCircle2,
  Download,
  Gauge,
  Lock,
  MessageSquareWarning,
  Scale,
  Sparkles,
  Zap,
} from "lucide-react";
import { ReviewSentimentAnalyzer } from "@/components/sentiment/analyzer-tool";
import { site } from "@/lib/site";

const url = `${site.url}/tools/review-sentiment-analyzer`;

const title = "Free Review Sentiment Analysis — What Customers Hate";
const description =
  "Upload a CSV or a reviews page URL and every review comes back positive, negative or neutral, with complaints ranked by frequency. Free, no sign-up.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "sentiment analysis tool",
    "free sentiment analysis tool",
    "review sentiment analysis",
    "customer review sentiment analysis",
    "sentiment analysis of customer reviews",
    "product review sentiment analysis",
    "csv sentiment analysis",
    "bulk sentiment analysis",
    "sentiment analysis online",
    "sentiment analyzer",
    "text sentiment analysis",
    "analyse customer feedback",
    "amazon review sentiment analysis",
    "google review sentiment analysis",
    "survey response sentiment analysis",
    "nps comment analysis",
    "analyse reviews from a url",
    "sentiment analysis from a web page",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is sentiment analysis?",
    a: "Sentiment analysis is the automatic classification of text as positive, negative or neutral. It is used on customer reviews, survey answers, support tickets and social posts to turn thousands of free-text comments into counts you can track. Most systems also return a score — often between -1 and +1 — so you can rank the strongest complaints and the strongest praise rather than only counting labels.",
  },
  {
    q: "How does sentiment analysis work?",
    a: "There are two main approaches. Lexicon methods score each word against a dictionary of positive and negative terms, then adjust for negation (“not good”), intensifiers (“very good”) and punctuation, and add the results up. Machine learning methods instead learn from thousands of labelled examples, and modern ones use transformer language models that read the whole sentence in context. Lexicons are transparent and instant; models handle nuance better but are harder to explain.",
  },
  {
    q: "How accurate is sentiment analysis?",
    a: "Around 80-85% agreement with human labels is typical on short product reviews, and large language models push that into the low 90s on clean English text. Human annotators only agree with each other about 80-90% of the time, so that is roughly the ceiling. Accuracy falls on sarcasm, mixed reviews that praise one thing and criticise another, domain jargon, and comparisons such as “better than the last one”. Treat the aggregate trend as reliable and any single row as a suggestion.",
  },
  {
    q: "What is a good sentiment score?",
    a: "For customer reviews, 70-80% positive is normal and healthy, because people who bother to review are skewed towards the happy and the furious. Anything below 60% positive usually signals a real product or delivery problem. The level matters less than the trend: a ten-point drop in positive share over a month is more informative than the absolute figure, and comparing your own categories against each other beats comparing against an industry benchmark.",
  },
  {
    q: "What is the difference between sentiment analysis and NPS?",
    a: "NPS is a number the customer gives you; sentiment analysis is a number you infer from what they wrote. NPS asks how likely someone is to recommend you on a 0-10 scale and buckets them into promoters, passives and detractors. Sentiment analysis reads the free-text comment instead, which is where the reason lives. They are complementary: the score tells you how bad it is, the comments tell you why, and running sentiment analysis over NPS verbatims connects the two.",
  },
  {
    q: "How do you analyse customer reviews at scale?",
    a: "Export the reviews to one row per comment, classify each for sentiment, then group by something you can act on — product, month, channel, star rating — and look at the differences rather than the overall average. Pull out the words that appear far more often in negative reviews than positive ones; those are your themes. Then read a sample of the extremes by hand. Automated scoring finds where to look, but the fix almost always comes from reading the actual sentences. The tool on this page does the first pass.",
  },
  {
    q: "Can sentiment analysis detect sarcasm?",
    a: "Mostly not. “Great, another broken zip” contains only positive words, so lexicon methods score it positive and even trained models get it wrong more often than not — published accuracy on sarcasm benchmarks sits well below general sentiment accuracy. The practical defences are to read the extremes manually, to cross-check sentiment against the star rating where you have one, and to accept that a small share of mislabelled rows does not move an aggregate built from thousands.",
  },
  {
    q: "What is the difference between sentiment analysis and emotion detection?",
    a: "Sentiment analysis places text on a single scale from negative to positive. Emotion detection assigns discrete feelings instead — anger, joy, sadness, fear, surprise, disgust — so two reviews that are equally negative can be separated into one that is furious and one that is disappointed. Emotion models are less accurate because the categories overlap and people label them inconsistently. Start with sentiment, add emotion only if the distinction would change what you do.",
  },
];

const highlights = [
  {
    icon: Scale,
    title: "Neutral is allowed to be neutral",
    body: "A review that just states when the parcel arrived is not praise and not a complaint. It gets labelled neutral instead of being shoved onto one side to make the chart look tidier.",
  },
  {
    icon: Zap,
    title: "The whole file, instantly",
    body: "Nothing to install, no queue, no per-review charge. The file is done by the time you let go of the mouse.",
  },
  {
    icon: Lock,
    title: "Your file never leaves the tab",
    body: "Reading and scoring both happen in your browser. Customer verbatims are usually personal data, and this way they stay on your machine rather than crossing someone else's server.",
  },
  {
    icon: Sparkles,
    title: "You can see why it decided that",
    body: "Every review shows the words that pushed it positive or negative, so you can check its reasoning and disagree with it when it gets one wrong.",
  },
  {
    icon: MessageSquareWarning,
    title: "Finds the five-star complaints",
    body: "If your file has star ratings, it pulls out the reviews where the stars and the words do not match. That list is usually the most useful thing in the file.",
  },
  {
    icon: Download,
    title: "CSV export, no sign-up",
    body: "Every row with its label and score, plus a summary of counts and driving terms. Opens in Excel, Sheets or Numbers.",
  },
];

const steps = [
  {
    name: "Export your reviews to CSV",
    text: "From Shopify, Trustpilot, Google Business, Zendesk, a survey tool or your own database. Keep the review text in one column; a star rating column is useful but optional.",
  },
  {
    name: "Drop the file on the box",
    text: "It finds the review column on its own and scores every row right here in the browser. Nothing uploads. If it picked the wrong column, change it and the results update straight away. Paste a URL into the review box and it spots that too, and offers to fetch the page instead.",
  },
  {
    name: "Or skip the export and paste the URL",
    text: "Give it the address of a reviews page instead. We fetch the page once, strip the navigation and scripts, and score each passage on it as its own review — because a page of reviews is many opinions, not one. Every passage is listed back with its score, so you can see exactly what was read.",
  },
  {
    name: "Work from the negatives and the mismatches",
    text: "Filter to negative, read the most-mentioned complaint terms, then check the rows where the stars and the words disagree. Download the CSV and hand it to whoever owns the fix.",
  },
];

export default function ReviewSentimentPage() {
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
            <span>Review sentiment analysis</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free review sentiment analysis
          </h1>
          <p className="mt-4 text-base text-sub text-pretty sm:text-lg">
            You have hundreds of reviews and nobody has time to read them. Upload
            a CSV with your review text in one column, paste a single review, or
            give it the address of a reviews page — every review comes back
            labelled positive, negative or neutral, with the complaints ranked by
            how often they come up and a CSV you can hand to whoever owns the fix.
            The scoring runs in your browser, so your file never leaves your
            machine; a URL is the one thing our server fetches for you, because a
            browser cannot read somebody else&rsquo;s page on its own.
          </p>

          <div className="mt-8">
            <ReviewSentimentAnalyzer />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Nothing uploaded",
              "Free",
              "Shows its working",
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
          What the sentiment analyzer gives you
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
            How to run sentiment analysis on customer reviews
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
            What it does not do
          </h2>
          <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Sarcasm.</strong> &ldquo;Brilliant, another
              week without my order&rdquo; scores positive. No sentiment tool reads
              sarcasm reliably, and any that claims to is measuring something else.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">English only.</strong> Reviews in
              other languages come back with a confident-looking score that means
              nothing, rather than an error, so filter mixed files first.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Split a review into topics.</strong>{" "}
              It judges a review as a whole, not &ldquo;happy about delivery, cross
              about the price&rdquo;. The most-mentioned words get you most of the
              way there.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Know your product&rsquo;s own words.</strong>{" "}
              A word that spells trouble in your category but is ordinary English
              reads as neutral. Skim the word lists and you will spot these quickly.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">Storage or monitoring.</strong> Nothing is
              saved, so there is no history, no dashboard and no alert when sentiment
              drops. Download the CSV if you want to keep the result.
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
          <h2 className="flex items-center gap-2 font-display text-2xl tracking-tight text-ink sm:text-3xl">
            <Gauge size={20} className="text-accent" />
            Reviews are one input
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            The same afternoon you find out what customers complain about, it is worth
            knowing what your site says to the people searching for you. That is the{" "}
            <Link
              href="/tools/seo-audit"
              className="font-medium text-accent hover:text-accent-hi"
            >
              free SEO audit tool
            </Link>{" "}
            and the{" "}
            <Link
              href="/tools/broken-link-checker"
              className="font-medium text-accent hover:text-accent-hi"
            >
              broken link checker
            </Link>
            .
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
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "Meelu Free Review Sentiment Analysis Tool",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Labels every review in a CSV positive, negative or neutral",
                "Finds the review and rating columns for you",
                "Shows the words behind every score",
                "Ranks the complaints and the praise by how often they come up",
                "Flags reviews where the star rating and the wording disagree",
                "Runs entirely in the browser — no upload",
                "CSV export of every row and of the summary",
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
              name: "How to run sentiment analysis on a CSV of customer reviews",
              description:
                "Export reviews to CSV, drop the file in the browser, and read every review back labelled positive, negative or neutral.",
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
                  name: "Review sentiment analysis",
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
