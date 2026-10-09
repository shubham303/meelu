import dns from "node:dns";
import net from "node:net";

const PRIVATE_RANGES = new net.BlockList();

for (const [address, prefix] of [
  ["0.0.0.0", 8],
  ["10.0.0.0", 8],
  ["100.64.0.0", 10],
  ["127.0.0.0", 8],
  ["169.254.0.0", 16],
  ["172.16.0.0", 12],
  ["192.0.0.0", 24],
  ["192.168.0.0", 16],
  ["198.18.0.0", 15],
  ["224.0.0.0", 4],
  ["240.0.0.0", 4],
]) {
  PRIVATE_RANGES.addSubnet(address, prefix, "ipv4");
}

for (const [address, prefix] of [
  ["::", 128],
  ["::1", 128],
  ["fc00::", 7],
  ["fe80::", 10],
  ["ff00::", 8],
]) {
  PRIVATE_RANGES.addSubnet(address, prefix, "ipv6");
}

function bareHost(hostname) {
  return String(hostname ?? "").replace(/^\[|\]$/g, "");
}

export function isPrivateAddress(hostname) {
  const host = bareHost(hostname);
  const family = net.isIP(host);
  if (family === 0) return false;
  return PRIVATE_RANGES.check(host, family === 4 ? "ipv4" : "ipv6");
}

export function privateHostError(hostname) {
  return new Error(`${bareHost(hostname)} is a private or local address; Meelu only fetches public sites.`);
}

export async function isPublicHost(hostname) {
  const host = bareHost(hostname);
  if (!host) return false;
  if (net.isIP(host)) return !isPrivateAddress(host);
  try {
    const addresses = await dns.promises.lookup(host, { all: true, verbatim: true });
    return addresses.length > 0 && addresses.every((a) => !isPrivateAddress(a.address));
  } catch {
    return false;
  }
}

export async function isPublicWebUrl(url) {
  let parsed;
  try {
    parsed = new URL(url);
  } catch {
    return false;
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") return false;
  return isPublicHost(parsed.hostname);
}

export function publicLookup(hostname, options, callback) {
  dns.lookup(hostname, { ...options, all: true }, (err, addresses) => {
    if (err) {
      callback(err);
      return;
    }
    if (addresses.length === 0 || addresses.some((a) => isPrivateAddress(a.address))) {
      callback(privateHostError(hostname));
      return;
    }
    if (options?.all) {
      callback(null, addresses);
      return;
    }
    callback(null, addresses[0].address, addresses[0].family);
  });
}
