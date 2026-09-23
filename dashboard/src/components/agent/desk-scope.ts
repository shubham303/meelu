import { WEBSITE_DESKS } from "@/components/desks";

export type DeskId =
  | "overview"
  | "site"
  | "pages"
  | "content"
  | "leads"
  | "analytics";

export function deskLabel(deskId: string): string {
  return WEBSITE_DESKS.find((d) => d.id === deskId)?.label ?? deskId;
}

export function deskHref(deskId: string): string {
  return WEBSITE_DESKS.find((d) => d.id === deskId)?.href ?? "/dashboard";
}

export function linkHref(link: { desk: string; id?: string | null }): string {
  const base = deskHref(link.desk);
  return link.id ? `${base}?focus=${encodeURIComponent(link.id)}` : base;
}

export function deskStage(deskId: string): string | undefined {
  return WEBSITE_DESKS.find((d) => d.id === deskId)?.stage;
}
