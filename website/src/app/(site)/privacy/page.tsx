import type { Metadata } from "next";
import { site } from "@/lib/site";
import {
  LegalEmail,
  LegalList,
  LegalPage,
  LegalSection,
  legalJsonLd,
  legalLinkClass,
} from "@/components/legal-page";

const title = "Privacy Policy";
const path = "/privacy";
const description =
  "What the Meelu app and website collect, why, where it is stored, who it is shared with, and how to delete it. Includes how Meelu handles Google Search Console and Google Analytics data.";

const EFFECTIVE = "2026-10-20";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}${path}` },
  openGraph: { title, description, url: `${site.url}${path}`, type: "website" },
};

const sections = [
  { id: "who", label: "1. Who we are" },
  { id: "collect", label: "2. What we collect" },
  { id: "google", label: "3. Google user data" },
  { id: "ai", label: "4. AI providers" },
  { id: "use", label: "5. How we use it" },
  { id: "share", label: "6. Who we share it with" },
  { id: "retention", label: "7. How long we keep it" },
  { id: "rights", label: "8. Your choices and rights" },
  { id: "security", label: "9. Security" },
  { id: "children", label: "10. Children" },
  { id: "changes", label: "11. Changes to this policy" },
  { id: "contact", label: "12. Contact" },
] as const;

const strong = "font-medium text-ink";

export default function PrivacyPage() {
  return (
    <LegalPage
      title={title}
      intro="This policy explains what the Meelu desktop app and the meelu.tech website collect, why, where it is kept, and how you can delete it. We collect only what the product needs to work."
      effective={EFFECTIVE}
      sections={sections}
      jsonLd={legalJsonLd({ title, path, description, effective: EFFECTIVE })}
    >
      <LegalSection id="who" heading="1. Who we are">
        <p>
          Meelu is run by {site.author.name} as a sole proprietor, based in India.
          &ldquo;Meelu&rdquo;, &ldquo;we&rdquo; and &ldquo;us&rdquo; in this policy mean
          {" "}{site.author.name}. Meelu is responsible for the personal data described here.
          You can reach us at <LegalEmail />.
        </p>
        <p>
          This policy covers the Meelu desktop app, the Meelu account and servers behind it,
          and the website at {site.url.replace(/^https?:\/\//, "")}.
        </p>
      </LegalSection>

      <LegalSection id="collect" heading="2. What we collect">
        <p>
          <strong className={strong}>Your account.</strong> Your email address, your name, and
          your password, which is stored only as a one-way hash. We keep sign-in sessions so you
          stay signed in.
        </p>
        <p>
          <strong className={strong}>Websites you add.</strong> The domain, name, target markets
          and social profile links you enter. The app crawls the public pages of your website and
          we store what it finds: page addresses, titles, headings, text, links, technical
          issues, and short classifications of each page.
        </p>
        <p>
          <strong className={strong}>Google data you connect.</strong> Search Console and Google
          Analytics reports for your website, if you choose to connect them. Section 3 covers
          this in detail.
        </p>
        <p>
          <strong className={strong}>Work you create in the app.</strong> Content drafts, notes,
          saved reports, analytics chats, plans and the suggestions Meelu makes for your
          website, and whether you approved or rejected them.
        </p>
        <p>
          <strong className={strong}>Keyword and social data.</strong> Keywords and competitor
          domains you track, their search volumes and rankings, and, if you use social listening,
          the topics you watch and the public posts found for them.
        </p>
        <p>
          <strong className={strong}>Leads.</strong> If you use Find Leads, the briefs you write
          and the people found for them from public sources: their public name, handle, headline
          and profile link, an email address only when a public page prints it, and the public
          posts behind the reason Meelu gives. Meelu does not send messages to them, store your
          messages or track replies.
        </p>
        <p>
          <strong className={strong}>Billing.</strong> Your credit balance, a history of credit
          charges, and a record of each payment (amount, status and the payment
          provider&rsquo;s reference). Card details are entered with our payment provider and
          never reach us.
        </p>
        <p>
          <strong className={strong}>Usage records.</strong> For each AI request we log the
          model, the number of tokens, the cost and whether it succeeded, so we can charge
          credits correctly. We do not keep the text of your conversations in these logs.
        </p>
        <p>
          <strong className={strong}>On your device.</strong> The app keeps its settings, your
          Google connection tokens and, if you add one, your own Anthropic API key on your
          computer, encrypted with your operating system&rsquo;s secure storage (Keychain on
          macOS). The app checks meelu.tech for new versions; that check sends no personal data.
        </p>
        <p>
          <strong className={strong}>On this website.</strong> We use Google Analytics to count
          visits and see which pages are read. When you download the app we ask for your email
          address and country; you can skip this. If you give them, we store them with the build
          you chose so we can tell you about fixes and new versions. If you joined the download
          waitlist, we keep the email address and platform you gave so we can tell you about
          Meelu. The free tools keep nothing you submit:
          most run in your browser, and the ones that fetch a page do so once and discard it.
        </p>
      </LegalSection>

      <LegalSection id="google" heading="3. Google user data">
        <p>
          You can connect Google Search Console and Google Analytics to Meelu. Connecting is
          optional, and you choose which Google account and which property to use. Meelu asks
          for read-only access only:
        </p>
        <LegalList>
          <li>
            <strong className={strong}>Search Console</strong> (
            <code className="font-mono text-sm">webmasters.readonly</code>): search performance
            for your website &mdash; queries, pages, clicks, impressions, click-through rate,
            average position, country and device &mdash; and the index status of your pages.
          </li>
          <li>
            <strong className={strong}>Google Analytics 4</strong> (
            <code className="font-mono text-sm">analytics.readonly</code>): aggregated reports
            for your website &mdash; sessions, users, page views, engagement, key events and
            revenue, broken down by date, page, landing page, traffic channel and source,
            country, device and browser. These are totals, not records of individual visitors.
          </li>
        </LegalList>
        <p>
          <strong className={strong}>Why we use it.</strong> To show you how your website
          performs in search and in traffic, to let the Meelu assistant answer your questions
          about that data, and to ground its suggestions (for example, which page to improve
          for which query) in your real numbers.
        </p>
        <p>
          <strong className={strong}>Where it is stored.</strong> The Google sign-in token
          (a refresh token) stays on your computer, encrypted in your operating system&rsquo;s
          secure storage, and is never sent to our servers. The app uses it to fetch your
          reports from Google and sends the report data to your Meelu account on our servers,
          where it is stored with your website so the dashboard and the assistant can read it.
        </p>
        <p>
          <strong className={strong}>AI processing.</strong> When you ask the Meelu assistant
          about your search or traffic data, the relevant parts of that data are sent to the AI
          model that answers you. By default this goes through OpenRouter to the model provider
          you selected in the app (such as Anthropic, OpenAI or DeepSeek). If you added your own
          Anthropic API key, it goes directly to Anthropic under your own account. The data is
          sent only to answer your request.
        </p>
        <p>
          <strong className={strong}>
            We do not use Google user data to develop, improve or train AI or machine learning
            models, and we do not allow the AI providers we send it to to use it for training.
          </strong>
        </p>
        <p>
          <strong className={strong}>What we never do.</strong> We do not sell Google user data.
          We do not use it for advertising, retargeting or interest-based ads. We do not transfer
          it to anyone except as needed to provide the features you use (see section 6), to
          comply with the law, or as part of a sale of the business with notice to you. No
          person at Meelu reads it unless you ask us to (for example, for support), it is needed
          for security, or the law requires it.
        </p>
        <p>
          <strong className={strong}>Revoking access and deleting the data.</strong> You can
          disconnect Search Console or Google Analytics at any time on the Connections screen in
          the app, which deletes the token from your computer. You can also revoke Meelu&rsquo;s
          access at{" "}
          <a
            href="https://myaccount.google.com/permissions"
            className={legalLinkClass}
            target="_blank"
            rel="noopener noreferrer"
          >
            myaccount.google.com/permissions
          </a>
          . Deleting a website in the app deletes all Google data stored for it from our
          servers. To delete everything, ask us to delete your account (section 8).
        </p>
        <p className="rounded-xl border border-edge bg-panel p-4 text-ink">
          Meelu&rsquo;s use and transfer to any other app of information received from Google
          APIs will adhere to{" "}
          <a
            href="https://developers.google.com/terms/api-services-user-data-policy"
            className={legalLinkClass}
            target="_blank"
            rel="noopener noreferrer"
          >
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements.
        </p>
      </LegalSection>

      <LegalSection id="ai" heading="4. AI providers">
        <p>
          Meelu&rsquo;s assistant and its page analysis use large language models. What you type,
          and the data the assistant needs to answer (your pages, keywords, reports), is sent to
          the model you selected through OpenRouter, or directly to Anthropic if you use your own
          key. Page classification on our servers uses a model through OpenRouter and sends only
          the public text of your website&rsquo;s pages. We do not use your data to train models.
        </p>
      </LegalSection>

      <LegalSection id="use" heading="5. How we use it">
        <LegalList>
          <li>to run the features you use and show you your data;</li>
          <li>to charge credits and process payments;</li>
          <li>to send account emails, such as sign-up verification codes;</li>
          <li>to keep the service secure and prevent abuse;</li>
          <li>to comply with the law.</li>
        </LegalList>
        <p>
          We do not sell your personal data, we do not use it for advertising, and we do not send
          marketing email.
        </p>
      </LegalSection>

      <LegalSection id="share" heading="6. Who we share it with">
        <p>We share data only with the services Meelu runs on, and only what each one needs:</p>
        <LegalList>
          <li>
            <strong className={strong}>Hostinger</strong> &mdash; the servers that host our
            database and the Meelu service.
          </li>
          <li>
            <strong className={strong}>Cloudflare</strong> &mdash; network protection for our
            domains, and storage for database backups, app downloads and the waitlist.
          </li>
          <li>
            <strong className={strong}>OpenRouter</strong> and the AI model provider you choose
            &mdash; to answer your requests (section 4).
          </li>
          <li>
            <strong className={strong}>Anthropic</strong> &mdash; only if you add your own
            Anthropic API key.
          </li>
          <li>
            <strong className={strong}>DataForSEO</strong> &mdash; the keywords and domains you
            ask about, to fetch search volumes and rankings.
          </li>
          <li>
            <strong className={strong}>Apify</strong> &mdash; the topics you watch in social
            listening and the searches Find Leads runs, to find public posts and public profiles,
            and the profile links of shortlisted people, to read their recent public posts.
          </li>
          <li>
            <strong className={strong}>Composio</strong> &mdash; only if you connect your own
            email, CMS, CRM, docs or social account to a website. Composio holds that
            account&rsquo;s sign-in and runs the actions you approve on it: reading mail, contacts,
            documents or posts, saving drafts or records, and posting a reply you approved. Disconnecting the account or deleting the website removes it from
            Composio.
          </li>
          <li>
            <strong className={strong}>Dodo Payments</strong> &mdash; to process credit
            purchases.
          </li>
          <li>
            <strong className={strong}>Resend</strong> &mdash; to deliver account emails.
          </li>
          <li>
            <strong className={strong}>Google Analytics</strong> &mdash; visit statistics for
            this website only, not for the app.
          </li>
        </LegalList>
        <p>
          We may also disclose data if the law requires it, or to protect the rights and safety
          of Meelu and its users.
        </p>
      </LegalSection>

      <LegalSection id="retention" heading="7. How long we keep it">
        <LegalList>
          <li>Account data is kept until you ask us to delete your account.</li>
          <li>
            Website data, including Google data, is kept until you delete the website. A website
            that stays paused for lack of credits for 30 days is deleted with all its data.
          </li>
          <li>
            Public posts found by social listening are deleted 30 days after they were posted,
            together with your replies and statuses on them.
          </li>
          <li>
            Discarded leads are deleted 30 days after you discard them, and people Meelu judged not
            a fit are forgotten after 30 days. For both, only a short key such as a profile handle
            is kept, so the same person is not shown to you again.
          </li>
          <li>
            Payment and credit records are kept as long as tax and accounting law requires.
          </li>
          <li>Database backups are kept for a limited time and then overwritten.</li>
        </LegalList>
      </LegalSection>

      <LegalSection id="rights" heading="8. Your choices and rights">
        <p>You can:</p>
        <LegalList>
          <li>see and edit your website data in the app;</li>
          <li>disconnect Google services and delete websites in the app at any time;</li>
          <li>
            ask for a copy of your data, a correction, or deletion of your account and all its
            data, by emailing <LegalEmail /> from your account email. We act on requests within
            30 days.
          </li>
        </LegalList>
        <p>
          Depending on where you live, you may have further rights under laws such as the GDPR or
          India&rsquo;s Digital Personal Data Protection Act. Email us and we will help.
        </p>
      </LegalSection>

      <LegalSection id="security" heading="9. Security">
        <p>
          Data travels over HTTPS. Passwords are hashed. Each account&rsquo;s data is separated in
          the database so one account cannot read another&rsquo;s. Tokens and keys on your
          computer are encrypted by your operating system. No system is perfectly secure; if
          you find a problem, please tell us at <LegalEmail />.
        </p>
      </LegalSection>

      <LegalSection id="children" heading="10. Children">
        <p>
          Meelu is a business tool for people aged 18 and over. We do not knowingly collect data
          from children.
        </p>
      </LegalSection>

      <LegalSection id="changes" heading="11. Changes to this policy">
        <p>
          When this policy changes, we update the date at the top of this page. If a change
          affects how we use your data in a significant way, we will tell you by email or in the
          app before it takes effect.
        </p>
      </LegalSection>

      <LegalSection id="contact" heading="12. Contact">
        <p>
          {site.author.name}, Meelu &mdash; <LegalEmail />
        </p>
      </LegalSection>
    </LegalPage>
  );
}
