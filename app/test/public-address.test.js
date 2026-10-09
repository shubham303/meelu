import test from "node:test";
import assert from "node:assert/strict";
import { isPrivateAddress, isPublicHost, isPublicWebUrl } from "../src/main/public-address.js";

test("loopback, private, link-local and unspecified addresses are private", () => {
  for (const ip of [
    "127.0.0.1",
    "10.1.2.3",
    "172.16.0.1",
    "172.31.255.255",
    "192.168.1.1",
    "169.254.169.254",
    "100.64.0.1",
    "0.0.0.0",
    "::1",
    "[::1]",
    "::",
    "fd00::1",
    "fe80::1",
    "::ffff:127.0.0.1",
    "::ffff:7f00:1",
  ]) {
    assert.equal(isPrivateAddress(ip), true, ip);
  }
});

test("public addresses are not private", () => {
  for (const ip of ["8.8.8.8", "104.20.23.154", "172.66.147.243", "2606:4700::1", "::ffff:8.8.8.8"]) {
    assert.equal(isPrivateAddress(ip), false, ip);
  }
});

test("a hostname is not an address, so it is never private by itself", () => {
  assert.equal(isPrivateAddress("example.com"), false);
});

test("localhost and IP literals in a URL are refused", async () => {
  assert.equal(await isPublicHost("localhost"), false);
  assert.equal(await isPublicWebUrl("http://127.0.0.1:3000/"), false);
  assert.equal(await isPublicWebUrl("http://0x7f.1/"), false);
  assert.equal(await isPublicWebUrl("http://[::1]/"), false);
});

test("only http and https URLs count as web URLs", async () => {
  assert.equal(await isPublicWebUrl("file:///etc/passwd"), false);
  assert.equal(await isPublicWebUrl("ftp://8.8.8.8/"), false);
  assert.equal(await isPublicWebUrl("not a url"), false);
  assert.equal(await isPublicWebUrl("http://8.8.8.8/"), true);
});
