export interface TourTarget {
  selector?: string;
  text?: string;
  card?: boolean;
}

export interface TourStep {
  id: string;
  path: string;
  chapter: string;
  title: string;
  body: string;
  target?: TourTarget;
}

const D = "/demo/dashboard";

export const TOUR_STEPS: TourStep[] = [
  {
    id: "welcome",
    path: "/demo/signup",
    chapter: "Get started",
    title: "Welcome to the Meelu demo",
    body: "This tour walks the whole journey, from creating an account to every desk. Everything here is sample data for Ledgerly, a made-up bookkeeping app. Nothing you type leaves your browser. Click Next, or try each screen as you go.",
  },
  {
    id: "signup",
    path: "/demo/signup",
    chapter: "Get started",
    title: "Create your account",
    body: "An email and a password are all Meelu asks for. Then you confirm the email with a 6-digit code. Fill the form to try it: in the demo any email works and any six digits pass.",
    target: { selector: "form", card: true },
  },
  {
    id: "profile",
    path: "/demo/onboarding",
    chapter: "Get started",
    title: "Tell Meelu who it writes as",
    body: "This is you, not your business, so it stays the same for every website you add. Only your name is needed now. Your role, timezone, sign-off and voice can wait for Settings.",
    target: { text: "Who should Meelu write as?", card: true },
  },
  {
    id: "add-site",
    path: D,
    chapter: "Get started",
    title: "Add your website",
    body: "Add a website from the switcher at the top of the sidebar. Each website gets its own crawl, profile, data and desks, and you can switch between them at any time. The demo already holds Ledgerly.",
    target: { selector: '[aria-label="Switch website"], div.relative.px-2.pb-3 > button' },
  },
  {
    id: "site-profile",
    path: `${D}/site`,
    chapter: "Get started",
    title: "Check the website profile",
    body: "Meelu crawls the site and writes a profile of what you sell and to whom. Read it and correct it, because every desk reads it before it suggests anything.",
  },
  {
    id: "llm",
    path: `${D}/connections`,
    chapter: "Set up",
    title: "Choose the model",
    body: "Tasks run on a default model, paid from your credits at what the model costs, with no markup. Or save your own Anthropic key: calls then go from your device to Anthropic, billed to your Anthropic account, and the key never reaches Meelu.",
    target: { text: "Your Anthropic key", card: true },
  },
  {
    id: "connections",
    path: `${D}/connections`,
    chapter: "Set up",
    title: "Connect Search Console and Analytics",
    body: "Sign in with Google to connect Search Console and Google Analytics 4. Meelu then reads how Google sees each page and what visitors do. The sign-in stays on your device.",
    target: { text: "Connections" },
  },
  {
    id: "credits",
    path: `${D}/credits`,
    chapter: "Set up",
    title: "Top up credits",
    body: "Search data, AI model calls and websites are charged to one balance, at cost. Results already in Meelu's database are free. Every charge is listed under Activity.",
    target: { text: "Credits" },
  },
  {
    id: "overview",
    path: D,
    chapter: "The desks",
    title: "Overview",
    body: "Start here each day. It shows what is waiting on you and what each desk holds.",
  },
  {
    id: "pages",
    path: `${D}/site/pages`,
    chapter: "The desks",
    title: "Site: pages",
    body: "Every page the crawl has read. Search what the passages inside them actually say, and open a page to see what Meelu read on it.",
    target: { selector: `a[href="${D}/site"]` },
  },
  {
    id: "technical-seo",
    path: `${D}/site/technical-seo`,
    chapter: "The desks",
    title: "Site: technical SEO",
    body: "One tab per way of looking at the site: static HTML, desktop and mobile rendering. Each issue carries the pages it was found on. You decide what to fix, and a check you turn down stays turned down.",
  },
  {
    id: "structure",
    path: `${D}/site/structure`,
    chapter: "The desks",
    title: "Site: structure",
    body: "How pages are reached from the home page. Meelu suggests internal links to add or remove, and pillar pages where several pages split one search. It never changes your site on its own.",
  },
  {
    id: "seo",
    path: `${D}/seo`,
    chapter: "The desks",
    title: "SEO: what to target next",
    body: "Keyword clusters ranked by how winnable they are and how many people search them. Google sometimes serves fake results to rank trackers, so each results page is checked first and a poisoned one is not scored.",
    target: { selector: `a[href="${D}/seo"]` },
  },
  {
    id: "start-task",
    path: `${D}/seo`,
    chapter: "The desks",
    title: "Start a task",
    body: "Each card starts a task with your coworker, already scoped to this desk. It works through the data, shows its evidence and asks before it saves anything. Tasks run in the desktop app.",
    target: { text: "Start a task" },
  },
  {
    id: "competitors",
    path: `${D}/seo/competitors`,
    chapter: "The desks",
    title: "SEO: competitors and backlinks",
    body: "Domains chasing the same searchers for the same thing. Name the ones that matter to you, and their links feed your backlink opportunities.",
  },
  {
    id: "backlinks",
    path: `${D}/seo/backlinks`,
    chapter: "The desks",
    title: "SEO: backlink opportunities",
    body: "Sites that link to your competitors but not to you. Links that look spammy, paid or too weak to help are left out. You decide which sites to ask.",
  },
  {
    id: "tracked",
    path: `${D}/seo/tracked`,
    chapter: "The desks",
    title: "SEO: tracked keywords",
    body: "Twelve months of search demand for the keywords you track, next to where you rank for them in Search Console.",
  },
  {
    id: "search",
    path: `${D}/seo/search`,
    chapter: "The desks",
    title: "SEO: search performance",
    body: "Your Search Console data: clicks, impressions and positions per query and page, plus which pages Google has indexed. Ask what changed, what dropped and what is close to page one.",
  },
  {
    id: "traffic",
    path: `${D}/seo/traffic`,
    chapter: "The desks",
    title: "SEO: traffic",
    body: "Your Google Analytics data: where visitors come from, which pages they land on and what converts.",
  },
  {
    id: "content",
    path: `${D}/content`,
    chapter: "The desks",
    title: "Content",
    body: "Pages for your own website: title, H1, meta description, slug, target keyword and body, grounded in your site and search data. Checks flag readability, AI-sounding passages and text that repeats one of your pages. You publish the page yourself.",
    target: { selector: `a[href="${D}/content"]` },
  },
  {
    id: "social",
    path: `${D}/social-listening`,
    chapter: "The desks",
    title: "Social Listening",
    body: "Posts where a reply from you belongs, found from what you describe. Meelu suggests an angle. You decide which to answer, and you post it yourself.",
    target: { selector: `a[href="${D}/social-listening"]` },
  },
  {
    id: "analytics",
    path: `${D}/analytics`,
    chapter: "The desks",
    title: "Analytics",
    body: "Ask about your Search Console and Analytics data in plain words. Answers come with charts and the evidence behind them.",
    target: { selector: `a[href="${D}/analytics"]` },
  },
  {
    id: "reports",
    path: `${D}/reports`,
    chapter: "The desks",
    title: "Reports",
    body: "Results you asked Meelu to keep, from Analytics, SEO and Technical SEO, newest first.",
    target: { selector: `a[href="${D}/reports"]` },
  },
  {
    id: "notes",
    path: `${D}/notes`,
    chapter: "The desks",
    title: "Notes",
    body: "Tell your coworker something once and it lands here. It reads these before every task, and a rule here outranks whatever it was about to do.",
    target: { selector: `a[href="${D}/notes"]` },
  },
  {
    id: "settings",
    path: `${D}/settings`,
    chapter: "Done",
    title: "Settings",
    body: "Your name, role, sign-off and voice live here, and steer everything Meelu drafts. You can also make keys to connect your coworker to Claude Desktop or any MCP client.",
  },
  {
    id: "finish",
    path: D,
    chapter: "Done",
    title: "Meelu suggests, you decide",
    body: "Each desk has prompt chips that start a task with your coworker. Every change it wants to make waits for your yes. The web dashboard shows the same screens; the agent runs in the desktop app.",
  },
];
