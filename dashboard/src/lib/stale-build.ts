const STALE_BUILD = /ChunkLoadError|Loading chunk [\w-]+ failed|Loading CSS chunk|Failed to fetch dynamically imported module|Importing a module script failed/i;

const RELOADED_AT = "meelu-stale-build-reload";

export function shouldReloadForStaleBuild(error: Error): boolean {
  if (typeof window === "undefined" || !STALE_BUILD.test(`${error.name} ${error.message}`)) return false;
  try {
    return Date.now() - Number(window.sessionStorage.getItem(RELOADED_AT) ?? 0) > 60_000;
  } catch {
    return false;
  }
}

export function reloadForStaleBuild(): void {
  try {
    window.sessionStorage.setItem(RELOADED_AT, String(Date.now()));
  } catch {
    return;
  }
  window.location.reload();
}
