import {
  BarChart3,
  FileText,
  Globe,
  LayoutDashboard,
  NotebookPen,
  Radar,
  Search,
  Settings,
  type LucideIcon,
} from "lucide-react";

export type DeskStage = "know" | "decide" | "make" | "earn" | "measure";

export interface Desk {
  id: string;
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  stage?: DeskStage;
  blurb: string;
  scope: "site" | "global";
}

export const WEBSITE_DESKS: Desk[] = [
  {
    id: "overview",
    href: "/demo/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    exact: true,
    blurb: "What is waiting on you, and what each desk holds.",
    scope: "site",
  },
  {
    id: "site",
    href: "/demo/dashboard/site",
    label: "Site",
    icon: Globe,
    stage: "know",
    blurb: "The corpus and its shape — what your pages actually say.",
    scope: "site",
  },
  {
    id: "seo",
    href: "/demo/dashboard/seo",
    label: "SEO",
    icon: Search,
    stage: "decide",
    blurb: "How Google sees the site and what visitors do — Search Console and Analytics.",
    scope: "site",
  },
  {
    id: "content",
    href: "/demo/dashboard/content",
    label: "Content",
    icon: FileText,
    stage: "make",
    blurb: "Pages for your website — keyword, internal links, title, H1 and meta description, checked on every save.",
    scope: "site",
  },
  {
    id: "social-listening",
    href: "/demo/dashboard/social-listening",
    label: "Social Listening",
    icon: Radar,
    stage: "earn",
    blurb: "Conversations your site belongs in, found from what you describe — you decide which to answer.",
    scope: "site",
  },
  {
    id: "analytics",
    href: "/demo/dashboard/analytics",
    label: "Analytics",
    icon: BarChart3,
    stage: "measure",
    blurb: "Ask about your Search Console and Analytics data — answers with charts and evidence; keep the ones that matter as reports.",
    scope: "site",
  },
  {
    id: "notes",
    href: "/demo/dashboard/notes",
    label: "Notes",
    icon: NotebookPen,
    blurb: "What you have told your coworker once. It reads these before every task.",
    scope: "site",
  },
];

export const APP_DESKS: Desk[] = [
  {
    id: "settings",
    href: "/demo/dashboard/settings",
    label: "Settings",
    icon: Settings,
    blurb: "Websites, model and connectors.",
    scope: "global",
  },
];

export const GLOBAL_HOME = "/demo/dashboard/settings";

export const WEBSITE_HOME = "/demo/dashboard";

export const SITE_ROOT = "/demo/dashboard/site";

export const STAGE_LABEL: Record<DeskStage, string> = {
  know: "know",
  decide: "decide",
  make: "make",
  earn: "earn",
  measure: "measure",
};
