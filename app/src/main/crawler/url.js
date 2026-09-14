const TRACKING = new Set([
  "gclid",
  "fbclid",
  "msclkid",
  "mc_cid",
  "mc_eid",
  "igshid",
  "ref",
  "_hsenc",
  "_hsmi",
]);

export function normalise(url) {
  try {
    const u = new URL(url);
    u.hash = "";
    u.hostname = u.hostname.toLowerCase();
    for (const key of [...u.searchParams.keys()]) {
      if (key.startsWith("utm_") || TRACKING.has(key)) u.searchParams.delete(key);
    }
    u.searchParams.sort();
    if (u.pathname.length > 1 && u.pathname.endsWith("/")) u.pathname = u.pathname.slice(0, -1);
    return u.toString();
  } catch {
    return url;
  }
}

function host(url) {
  return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
}

export function sameSite(url, other) {
  try {
    return host(url) === host(other);
  } catch {
    return false;
  }
}

export function sameHost(url, other) {
  try {
    return new URL(url).hostname.toLowerCase() === new URL(other).hostname.toLowerCase();
  } catch {
    return false;
  }
}

export function otherHostForm(url, other) {
  return !sameHost(url, other) && sameSite(url, other);
}
