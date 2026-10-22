const OPENABLE = new Set(["http:", "https:", "mailto:", "tel:"]);

export function linkTarget(href: string | null, siteOrigin: string | undefined): string | null {
  const raw = href?.trim();
  if (!raw || raw.startsWith("#")) return null;
  if (raw.startsWith("/api/")) return raw;
  try {
    const url = siteOrigin ? new URL(raw, siteOrigin) : new URL(raw);
    return OPENABLE.has(url.protocol) ? url.toString() : null;
  } catch {
    return null;
  }
}

export function siteOriginOf(el: Element | null): string | undefined {
  return el?.closest("[data-site-origin]")?.getAttribute("data-site-origin") || undefined;
}

export function openDocLink(anchor: Element | null, host: Element | null): boolean {
  if (!anchor) return false;
  const target = linkTarget(anchor.getAttribute("href"), siteOriginOf(host));
  if (!target) return false;
  window.open(target, "_blank", "noopener,noreferrer");
  return true;
}
