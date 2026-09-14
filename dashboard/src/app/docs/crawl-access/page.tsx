import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { CodeBlock } from "@/components/docs/code-block";

export const metadata: Metadata = {
  title: "Let the crawler through",
  description:
    "If a firewall or bot protection blocks Meelu's crawler, grant it access with a secret header rather than an IP or user-agent rule.",
};

const CLOUDFLARE_EXPRESSION = `(http.request.headers["x-meelu-crawl"][0] eq "YOUR_TOKEN_HERE")`;

const HEADER = `X-Meelu-Crawl: YOUR_TOKEN_HERE`;

const NGINX = `location / {
  if ($http_x_meelu_crawl = "YOUR_TOKEN_HERE") {
    set $meelu_ok 1;
  }
}`;

export default function CrawlAccessPage() {
  return (
    <article className="space-y-10">
      <div>
        <Link
          href="/docs"
          className="inline-flex items-center gap-1.5 text-xs text-faint transition-colors hover:text-accent"
        >
          <ArrowLeft size={12} /> Docs
        </Link>
        <h1 className="mt-3 font-display text-3xl text-ink">Let the crawler through</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Meelu reads your website from your own machine, on your own connection. If your site
          sits behind Cloudflare, a WAF, or any bot protection, that traffic looks like a bot —
          because it is one — and gets challenged or blocked. This page is how you grant it
          access.
        </p>
      </div>

      <section>
        <h2 className="font-display text-lg text-ink">How to tell this is happening</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          The crawl finishes, but every page is recorded as blocked rather than missing. On the
          Site desk you&apos;ll see a wall of <code className="font-mono text-accent">403</code>{" "}
          responses, and the crawl notes will say the site refused the request. A page that
          returns 403 is not a broken page — it is your own firewall turning Meelu away.
        </p>
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">1. Copy your crawl access token</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Open the Website profile screen on the Site desk in the app. Each website has its own
          token — a long random string made on this machine and kept here, never sent to the
          Meelu server. Copy it, and replace{" "}
          <code className="font-mono text-accent">YOUR_TOKEN_HERE</code> with it everywhere below.
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          Every crawl request Meelu makes to your site carries it as a header:
        </p>
        <CodeBlock className="mt-3" label="request header" code={HEADER} />
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">2. Add the rule — Cloudflare</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          In the Cloudflare dashboard, go to <span className="text-ink">Security → WAF → Custom
          rules</span> and create a rule. Custom rules are available on the free plan.
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          Set the expression, using the Edit expression tab:
        </p>
        <CodeBlock className="mt-3" label="expression" code={CLOUDFLARE_EXPRESSION} />
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          Then set the action to <span className="text-ink">Skip</span>, and tick{" "}
          <span className="text-ink">All remaining custom rules</span> plus{" "}
          <span className="text-ink">Bot Fight Mode</span>. Deploy it, and move the rule above any
          rule that would otherwise block bots.
        </p>
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">Other firewalls</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          The same header works anywhere. Whatever sits in front of your site, the rule is
          &ldquo;if this header matches this value, skip the bot checks&rdquo;. On nginx it is a
          variable test:
        </p>
        <CodeBlock className="mt-3" label="nginx" code={NGINX} />
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          It also works for a staging site behind HTTP auth, and for exempting the crawler from
          rate limits.
        </p>
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">Why a header, and not an IP</h2>
        <div className="mt-2 space-y-3 text-sm leading-relaxed text-sub">
          <p>
            <span className="text-ink">An IP allowlist cannot work.</span> The crawl runs on your
            machine, on a home or office connection whose address changes. There is no stable
            address to allow.
          </p>
          <p>
            <span className="text-ink">A user-agent rule is not a secret.</span> Meelu identifies
            itself honestly as <code className="font-mono text-accent">MeeluSEO/1.0</code>, which
            means anyone can type that string and walk through a rule built on it.
          </p>
          <p>
            <span className="text-ink">A secret header is neither.</span> Nobody can guess it, it
            travels inside TLS so it is never visible in transit, and if it ever leaks you rotate
            it on the Website profile screen and update one rule.
          </p>
        </div>
      </section>

      <section>
        <p className="flex items-start gap-2 rounded-xl border border-edge bg-panel p-3.5 text-xs leading-relaxed text-sub">
          <ShieldCheck size={15} className="mt-px shrink-0 text-good" />
          <span>
            <span className="text-ink">This is for your own website.</span> A token grants access
            to a site you control. It is not a way around someone else&apos;s bot protection —
            if another site challenges the crawler, that is its owner&apos;s decision, and Meelu
            records the pages as blocked and leaves them alone.
          </span>
        </p>
      </section>
    </article>
  );
}
