import type { Metadata } from "next";
import Link from "next/link";
import { site } from "@/lib/site";
import {
  LegalEmail,
  LegalList,
  LegalPage,
  LegalSection,
  legalJsonLd,
  legalLinkClass,
} from "@/components/legal-page";

const title = "Terms of Service";
const path = "/terms";
const description =
  "The terms for using the Meelu desktop app, your Meelu account and credits, the meelu.tech website and its free tools.";

const EFFECTIVE = "2026-10-12";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}${path}` },
  openGraph: { title, description, url: `${site.url}${path}`, type: "website" },
};

const sections = [
  { id: "agreement", label: "1. Agreement" },
  { id: "service", label: "2. The service" },
  { id: "account", label: "3. Your account" },
  { id: "credits", label: "4. Credits and payments" },
  { id: "your-data", label: "5. Your data" },
  { id: "connections", label: "6. Connected services" },
  { id: "ai-output", label: "7. AI output and suggestions" },
  { id: "acceptable-use", label: "8. Acceptable use" },
  { id: "ip", label: "9. Our property" },
  { id: "termination", label: "10. Ending your use" },
  { id: "disclaimer", label: "11. Disclaimer" },
  { id: "liability", label: "12. Limitation of liability" },
  { id: "law", label: "13. Governing law" },
  { id: "changes", label: "14. Changes" },
  { id: "contact", label: "15. Contact" },
] as const;

export default function TermsPage() {
  return (
    <LegalPage
      title={title}
      intro="These terms cover the Meelu desktop app, your Meelu account and credits, and the meelu.tech website with its free tools. They are short and in plain English."
      effective={EFFECTIVE}
      sections={sections}
      jsonLd={legalJsonLd({ title, path, description, effective: EFFECTIVE })}
    >
      <LegalSection id="agreement" heading="1. Agreement">
        <p>
          Meelu is run by {site.author.name} as a sole proprietor, based in India
          (&ldquo;Meelu&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;). By creating an account,
          using the app or using this website, you agree to these terms and to our{" "}
          <Link href="/privacy" className={legalLinkClass}>
            Privacy Policy
          </Link>
          . If you do not agree, do not use Meelu. If you use Meelu for a company, you confirm
          you may accept these terms for it.
        </p>
      </LegalSection>

      <LegalSection id="service" heading="2. The service">
        <p>
          Meelu is a desktop app with an AI assistant for digital marketing. It crawls your
          website, reads the Google Search Console and Google Analytics data you connect, tracks
          keywords, drafts web pages and suggests improvements. This website also offers free
          marketing tools that need no account.
        </p>
        <p>
          Meelu is in early access. Features may change, and we may add, change or remove parts
          of the service at any time.
        </p>
      </LegalSection>

      <LegalSection id="account" heading="3. Your account">
        <LegalList>
          <li>You must be at least 18 years old to create an account.</li>
          <li>Give a real email address and keep your password secure.</li>
          <li>You are responsible for everything done with your account.</li>
          <li>Tell us at once if you think someone else has used it.</li>
        </LegalList>
      </LegalSection>

      <LegalSection id="credits" heading="4. Credits and payments">
        <LegalList>
          <li>
            Meelu is paid for with prepaid credits. One credit is one US dollar. Current prices
            are on the{" "}
            <Link href="/pricing" className={legalLinkClass}>
              pricing page
            </Link>
            .
          </li>
          <li>
            Each website uses credits every day, and paid data and AI services use credits when
            they run. Every charge is shown in your credit history in the app.
          </li>
          <li>
            Payments are processed by Dodo Payments, which acts as the merchant of record and
            handles tax on your purchase.
          </li>
          <li>
            When your balance cannot cover a website&rsquo;s next day, that website is paused.
            Adding credits resumes it. A website paused for 30 days is deleted with its data.
          </li>
          <li>
            Credits have no cash value and cannot be transferred. Purchased credits are not
            refundable, except where the law requires a refund or we charged you in error. Free
            credits given at sign-up can be withdrawn if they are abused.
          </li>
          <li>We may change prices. A change does not affect credits you already bought.</li>
        </LegalList>
      </LegalSection>

      <LegalSection id="your-data" heading="5. Your data">
        <p>
          You own the data and content you bring to Meelu and the content Meelu drafts for you.
          You give us permission to store and process it only as needed to run the service for
          you, as described in the Privacy Policy.
        </p>
        <p>
          You must have the right to use what you add. Only add websites you own or are
          authorised to work on.
        </p>
      </LegalSection>

      <LegalSection id="connections" heading="6. Connected services">
        <p>
          When you connect Google Search Console, Google Analytics or another service, you
          authorise Meelu to read your data from it on your behalf. Your use of those services
          stays under their own terms. You can disconnect them at any time in the app.
        </p>
      </LegalSection>

      <LegalSection id="ai-output" heading="7. AI output and suggestions">
        <p>
          Meelu uses AI models and third-party data. Their output can be wrong, incomplete or
          out of date. Meelu suggests; you decide. It does not change your website on its own,
          and you are responsible for checking anything before you publish or act on it.
        </p>
        <p>
          Meelu and its free tools are not legal, financial or professional advice. Do not use
          the AI content detector as the only basis for a decision about a person.
        </p>
      </LegalSection>

      <LegalSection id="acceptable-use" heading="8. Acceptable use">
        <p>You agree not to:</p>
        <LegalList>
          <li>crawl or analyse websites you have no right to, or break any law using Meelu;</li>
          <li>use Meelu to create spam, malware, or unlawful, misleading or infringing content;</li>
          <li>
            try to get around credit charges, rate limits or security, or access other
            users&rsquo; data;
          </li>
          <li>overload, disrupt, or scrape the service or this website in bulk;</li>
          <li>resell the service or pass it off as your own.</li>
        </LegalList>
        <p>
          If you find a security issue, please report it to <LegalEmail /> instead of using it.
        </p>
      </LegalSection>

      <LegalSection id="ip" heading="9. Our property">
        <p>
          The Meelu name, logo, app and website belong to us, except for open source code, which
          is governed by its own licence. These terms do not give you any right to our brand.
        </p>
      </LegalSection>

      <LegalSection id="termination" heading="10. Ending your use">
        <p>
          You can stop using Meelu at any time and ask us to delete your account. We may suspend
          or close an account that breaks these terms or puts the service or other users at risk.
          If we close the service for reasons other than your breach, we will refund unused
          purchased credits.
        </p>
      </LegalSection>

      <LegalSection id="disclaimer" heading="11. Disclaimer">
        <p>
          Meelu is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without
          warranties of any kind, to the fullest extent the law allows. We do not promise that it
          will be uninterrupted, error-free, or that it will improve your rankings or traffic.
        </p>
      </LegalSection>

      <LegalSection id="liability" heading="12. Limitation of liability">
        <p>
          To the fullest extent the law allows, we are not liable for indirect or consequential
          losses, or for lost profits, revenue, data or goodwill. Our total liability for any
          claim is limited to the amount you paid us in the 12 months before the claim. Nothing
          here limits liability that cannot be limited by law.
        </p>
      </LegalSection>

      <LegalSection id="law" heading="13. Governing law">
        <p>
          These terms are governed by the laws of India. The courts of Pune, Maharashtra have
          jurisdiction over any dispute, without removing any right you have as a consumer to
          bring a claim where you live.
        </p>
      </LegalSection>

      <LegalSection id="changes" heading="14. Changes">
        <p>
          We may update these terms. The date at the top shows the current version. For
          important changes we will tell you by email or in the app before they take effect.
          Using Meelu after a change means you accept the new terms.
        </p>
      </LegalSection>

      <LegalSection id="contact" heading="15. Contact">
        <p>
          {site.author.name}, Meelu &mdash; <LegalEmail />
        </p>
      </LegalSection>
    </LegalPage>
  );
}
