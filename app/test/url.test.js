import test from "node:test";
import assert from "node:assert/strict";
import { onOrigin, otherHostForm, sameHost, sameSite } from "../src/main/crawler/url.js";

const BARE = "https://example.com/";
const WWW = "https://www.example.com/";

test("a www host and a bare host are not the same host", () => {
  assert.equal(sameHost(WWW, BARE), false);
  assert.equal(sameHost(BARE, WWW), false);
});

test("the same host in different case is one host", () => {
  assert.equal(sameHost("https://Example.com/a", "https://example.com/b"), true);
});

test("a different scheme does not change the host", () => {
  assert.equal(sameHost("http://example.com/a", "https://example.com/b"), true);
});

test("an unrelated domain is neither the same host nor a host form of it", () => {
  assert.equal(sameHost("https://other.example.net/", BARE), false);
  assert.equal(otherHostForm("https://other.example.net/", BARE), false);
});

test("otherHostForm catches exactly the www twin of the crawled host", () => {
  assert.equal(otherHostForm(WWW, BARE), true);
  assert.equal(otherHostForm(BARE, WWW), true);
  assert.equal(otherHostForm(BARE, BARE), false);
});

test("a subdomain that is not www is a separate host, not a host form", () => {
  assert.equal(sameHost("https://blog.example.com/", BARE), false);
  assert.equal(otherHostForm("https://blog.example.com/", BARE), false);
});

test("sameSite stays www-insensitive so citations are not inflated by a host twin", () => {
  assert.equal(sameSite(WWW, BARE), true);
});

test("a malformed URL is never treated as the same host", () => {
  assert.equal(sameHost("not a url", BARE), false);
  assert.equal(otherHostForm("not a url", BARE), false);
});

test("onOrigin moves the www twin of a URL onto the crawled host", () => {
  assert.equal(onOrigin("https://example.com/about?x=1", "https://www.example.com"), "https://www.example.com/about?x=1");
  assert.equal(onOrigin("http://www.example.com/a", "https://example.com"), "https://example.com/a");
});

test("onOrigin leaves the crawled host and unrelated hosts alone", () => {
  assert.equal(onOrigin("https://example.com/a", "https://example.com"), "https://example.com/a");
  assert.equal(onOrigin("https://other.example.net/a", "https://example.com"), "https://other.example.net/a");
});
