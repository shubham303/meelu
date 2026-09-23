export function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return null;
  }
}

export function dedupeKeysOf(p) {
  const keys = [];
  if (p.email) keys.push(p.email.toLowerCase());
  if (p.website) {
    const domain = domainOf(p.website);
    if (domain) keys.push(domain);
  }
  for (const [platform, handle] of Object.entries(p.channelHandles ?? {})) {
    keys.push(`${platform}:${String(handle).toLowerCase()}`);
  }
  return [...new Set(keys)];
}

export function dedupeProspects(prospects) {
  const seen = new Set();
  const out = [];
  for (const p of prospects) {
    const keys = dedupeKeysOf(p);
    const fallback = `name:${p.name.toLowerCase()}|${p.source}`;
    const check = keys.length ? keys : [fallback];
    if (check.some((k) => seen.has(k))) continue;
    for (const k of check) seen.add(k);
    out.push(p);
  }
  return out;
}
