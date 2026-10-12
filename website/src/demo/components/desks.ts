import {
  BarChart3,
  FileText,
  Globe,
  LayoutDashboard,
  NotebookPen,
  Radar,
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
    id: "content",
    href: "/demo/dashboard/content",
    label: "Content",
    icon: FileText,
    stage: "make",
    blurb: "Web pages for your own site — title, H1, meta description, slug, target keyword and body, checked before you publish them yourself.",
    scope: "site",
  },
  {
    id: "social-listening",
    href: "/demo/dashboard/social-listening",
    label: "Social Listening",
    icon: Radar,
    stage: "earn",
    blurb: "Conversations your site belongs in — questions to answer, mentions of you, and competitor threads.",
    scope: "site",
  },
  {
    id: "analytics",
    href: "/demo/dashboard/analytics",
    label: "Analytics",
    icon: BarChart3,
    stage: "measure",
    blurb: "Any tabular source in, tables and charts out. The measured half.",
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
