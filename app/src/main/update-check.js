const CHECK_EVERY_MS = 10 * 60 * 1000;
const FALLBACK_DOWNLOAD_URL = "https://meelu.tech/download";

function versionParts(version) {
  const match = /^v?(\d+)\.(\d+)\.(\d+)$/.exec(String(version ?? "").trim());
  return match ? match.slice(1).map(Number) : null;
}

export function isNewer(latest, current) {
  const a = versionParts(latest);
  const b = versionParts(current);
  if (!a || !b) return false;
  for (let i = 0; i < 3; i += 1) {
    if (a[i] !== b[i]) return a[i] > b[i];
  }
  return false;
}

export function installerUrl(manifest, platform, arch) {
  const url = manifest?.installers?.[`${platform}-${arch}`];
  return typeof url === "string" && url.startsWith("https://") ? url : FALLBACK_DOWNLOAD_URL;
}

export function availableUpdate(manifest, { currentVersion, platform, arch }) {
  if (!isNewer(manifest?.version, currentVersion)) return null;
  return {
    currentVersion,
    version: String(manifest.version).replace(/^v/, ""),
    downloadUrl: installerUrl(manifest, platform, arch),
  };
}

export function startUpdateCheck({ manifestUrl, currentVersion, onUpdate, log }) {
  let latest = null;
  if (!manifestUrl) {
    return {
      current: () => latest,
      checkNow: async () => ({ error: "Update checks run only in the installed app." }),
    };
  }

  const check = async () => {
    try {
      const res = await fetch(manifestUrl, { cache: "no-store", signal: AbortSignal.timeout(10_000) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const update = availableUpdate(await res.json(), {
        currentVersion,
        platform: process.platform,
        arch: process.arch,
      });
      if (update && update.version !== latest?.version) {
        latest = update;
        log(`update available: ${currentVersion} → ${update.version}`);
        onUpdate(update);
      }
      return { update };
    } catch (err) {
      log("update check failed:", err.message);
      return { error: "Could not reach the update server. Check your connection and try again." };
    }
  };

  void check();
  setInterval(() => void check(), CHECK_EVERY_MS).unref();
  return { current: () => latest, checkNow: check };
}
