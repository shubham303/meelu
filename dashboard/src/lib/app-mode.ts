export function isAppUserAgent(ua: string | null | undefined): boolean {
  return !!ua && ua.includes("Electron");
}
