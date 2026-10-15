import assert from "node:assert/strict";
import dns from "node:dns/promises";
import http from "node:http";
import type { AddressInfo } from "node:net";
import { after, afterEach, before, mock, test } from "node:test";
import { fetchUrl, isPrivateAddress } from "../../src/lib/seo-audit/net.ts";

let server: http.Server;
let port = 0;
let hits = 0;

before(async () => {
  server = http.createServer((_req, res) => {
    hits += 1;
    res.writeHead(200, { "content-type": "text/html" });
    res.end("<html><head><title>internal only</title></head></html>");
  });
  await new Promise<void>((done) => server.listen(0, "127.0.0.1", done));
  port = (server.address() as AddressInfo).port;
});

after(() => server.close());

afterEach(() => {
  mock.restoreAll();
  hits = 0;
});

test("a host that answers public for the check and loopback for the fetch is refused", async () => {
  let lookups = 0;
  mock.method(dns, "lookup", async () => {
    lookups += 1;
    const address = lookups === 1 ? "93.184.216.34" : "127.0.0.1";
    return [{ address, family: 4 }];
  });

  const result = await fetchUrl(`http://127.0.0.1.nip.io:${port}/`);

  assert.equal(hits, 0, "the request reached the loopback server");
  assert.ok(!result.html?.includes("internal only"));
  assert.ok(result.blockedReason, "the fetch is reported as blocked");
});

test("private and reserved addresses are recognised in every IPv6 spelling", () => {
  const blocked = [
    "127.0.0.1",
    "10.1.2.3",
    "172.17.0.1",
    "169.254.169.254",
    "::1",
    "::",
    "::127.0.0.1",
    "::7f00:1",
    "::ffff:127.0.0.1",
    "::ffff:7f00:1",
    "::ffff:a00:1",
    "64:ff9b::7f00:1",
    "2002:7f00:1::",
    "ff02::1",
    "100::1",
    "2001:db8::1",
    "2001:0:4136:e378::1",
    "fe80::1",
    "fd00::1",
    "fc00::1",
  ];
  for (const ip of blocked) assert.equal(isPrivateAddress(ip), true, ip);
});

test("public addresses stay allowed", () => {
  const allowed = ["93.184.216.34", "192.0.78.9", "8.8.8.8", "2606:4700::6810:84e5", "::ffff:8.8.8.8", "2a00:1450:4001::200e"];
  for (const ip of allowed) assert.equal(isPrivateAddress(ip), false, ip);
});
