import {
  BarChart3,
  FileText,
  Globe,
  LayoutDashboard,
  NotebookPen,
  Radar,
  Search,
  Send,
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
    href: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    exact: true,
    blurb: "What is waiting on you, and what each desk holds.",
    scope: "site",
  },
  {
    id: "site",
    href: "/dashboard/site",
    label: "Site",
    icon: Globe,
    stage: "know",
    blurb: "The corpus and its shape — what your pages actually say.",
    scope: "site",
  },
  {
    id: "seo",
    href: "/dashboard/seo",
    label: "SEO",
    icon: Search,
    stage: "decide",
    blurb: "Which page to add, edit or merge — from Search Console, keywords and competitors.",
    scope: "site",
  },
  {
    id: "content",
    href: "/dashboard/content",
    label: "Content",
    icon: FileText,
    stage: "make",
    blurb: "Everything you write — website copy or a post for any social channel, checked against its limits.",
    scope: "site",
  },
  {
    id: "leads",
    href: "/dashboard/leads",
    label: "Lead Management",
    icon: Send,
    stage: "earn",
    blurb: "Source and curate the people worth talking to — found, qualified, shortlisted.",
    scope: "site",
  },
  {
    id: "social-listening",
    href: "/dashboard/social-listening",
    label: "Social Listening",
    icon: Radar,
    stage: "earn",
    blurb: "Conversations your site belongs in — questions to answer, mentions of you, and competitor threads.",
    scope: "site",
  },
  {
    id: "analytics",
    href: "/dashboard/analytics",
    label: "Analytics",
    icon: BarChart3,
    stage: "measure",
    blurb: "Any tabular source in, tables and charts out. The measured half.",
    scope: "site",
  },
  {
    id: "notes",
    href: "/dashboard/notes",
    label: "Notes",
    icon: NotebookPen,
    blurb: "What you have told your coworker once. It reads these before every task.",
    scope: "site",
  },
];

export const APP_DESKS: Desk[] = [
  {
    id: "settings",
    href: "/dashboard/settings",
    label: "Settings",
    icon: Settings,
    blurb: "Websites, model and connectors.",
    scope: "global",
  },
];

export const GLOBAL_HOME = "/dashboard/settings";

export const WEBSITE_HOME = "/dashboard";

export const SITE_ROOT = "/dashboard/site";

export const STAGE_LABEL: Record<DeskStage, string> = {
  know: "know",
  decide: "decide",
  make: "make",
  earn: "earn",
  measure: "measure",
};
