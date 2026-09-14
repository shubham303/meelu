import assert from "node:assert/strict";
import { test } from "node:test";
import { SocialAdapter, SOCIAL_CAPABILITIES } from "../src/main/providers/social/adapter.js";
import { SocialMediaScheduler } from "../src/main/providers/social/scheduler.js";
import { toolHandlers, toolNames } from "../src/main/providers/tools.js";

class FakeAdapter extends SocialAdapter {
  static id = "fake";
  static name_ = "Fake";

  static get capabilities() {
    return new Set(SOCIAL_CAPABILITIES);
  }

  static get platforms() {
    return ["linkedin", "bluesky"];
  }

  constructor() {
    super();
    this.calls = [];
    this.profiles = [{ id: "p1", name: "Acme", status: "active", platform: "linkedin", avatarUrl: null }];
    this.posts = new Map();
  }

  async createAccount(name) {
    this.calls.push(["createAccount", name]);
    return { id: "grp_1" };
  }

  async connectLink(accountId, platform, redirectUrl) {
    this.calls.push(["connectLink", accountId, platform, redirectUrl]);
    return { url: `https://vendor/connect/${platform}`, expiresAt: null };
  }

  async listProfiles(accountId) {
    this.calls.push(["listProfiles", accountId]);
    return this.profiles;
  }

  async createPost(accountId, input) {
    this.calls.push(["createPost", accountId, input]);
    const post = { id: "post_1", body: input.body, status: "scheduled", scheduledAt: input.scheduledAt, platforms: [] };
    this.posts.set(post.id, post);
    return post;
  }

  async getPost(accountId, postId) {
    return this.posts.get(postId);
  }

  async deletePost(accountId, postId) {
    this.calls.push(["deletePost", accountId, postId]);
    this.posts.delete(postId);
  }

  async updatePost(accountId, postId, patch) {
    this.calls.push(["updatePost", accountId, postId, patch]);
    return { ...this.posts.get(postId), scheduledAt: patch.scheduledAt };
  }
}

class NarrowAdapter extends FakeAdapter {
  static id = "narrow";
  static name_ = "Narrow";

  static get capabilities() {
    return new Set(["profiles.list"]);
  }
}

function fakeMeelu({ account = null, pieces = {} } = {}) {
  const log = [];
  const state = { account, pieces };
  return {
    log,
    state,
    async request(path, { method = "GET", body, allow = [] } = {}) {
      log.push([method, path, body ?? null]);
      if (path === "/social/account" && method === "GET") {
        if (!state.account) {
          if (allow.includes(404)) return null;
          throw Object.assign(new Error("not found"), { status: 404 });
        }
        return state.account;
      }
      if (path === "/social/account" && method === "PUT") {
        state.account = { id: "acc_1", ...body };
        return state.account;
      }
      if (path === "/site") return { name: "Acme", domain: "acme.test" };
      if (path === "/social/channels/sync") return { synced: true };
      if (path.startsWith("/content/pieces/") && method === "PATCH") {
        const id = decodeURIComponent(path.split("/")[3]);
        state.pieces[id] = { ...state.pieces[id], ...body };
        return state.pieces[id];
      }
      if (path.startsWith("/content/pieces/")) {
        const id = decodeURIComponent(path.split("/")[3]);
        return state.pieces[id];
      }
      if (path.startsWith("/content/channels/")) return { timezone: "America/New_York" };
      throw new Error(`unexpected ${method} ${path}`);
    },
    async bytes() {
      throw new Error("no media in this test");
    },
  };
}

function scheduler({ adapters, connected, dflt = null, meelu }) {
  return new SocialMediaScheduler({
    adapters,
    store: {
      connected: (id) => (connected.includes(id) ? { apiKey: "k" } : null),
      defaultFor: () => dflt,
    },
    meelu,
  });
}

test("tools are defined as facade methods", () => {
  const names = toolNames(SocialMediaScheduler);
  assert.ok(names.includes("social_schedule_post"));
  const handlers = toolHandlers(scheduler({ adapters: [new FakeAdapter()], connected: [], meelu: fakeMeelu() }));
  assert.equal(handlers.size, names.length);
});

test("no provider connected surfaces a ProviderError", async () => {
  const s = scheduler({ adapters: [new FakeAdapter()], connected: [], meelu: fakeMeelu() });
  await assert.rejects(() => s.connectLink({ siteId: "s1", platform: "linkedin" }), (err) => err.code === "no_provider");
});

test("two connected providers without a default is ambiguous", async () => {
  const s = scheduler({
    adapters: [new FakeAdapter(), new NarrowAdapter()],
    connected: ["fake", "narrow"],
    meelu: fakeMeelu(),
  });
  await assert.rejects(() => s.connectLink({ siteId: "s1", platform: "linkedin" }), (err) => err.code === "ambiguous_provider");
});

test("a default resolves the ambiguity and a missing capability is not_supported", async () => {
  const s = scheduler({
    adapters: [new FakeAdapter(), new NarrowAdapter()],
    connected: ["fake", "narrow"],
    dflt: "narrow",
    meelu: fakeMeelu(),
  });
  await assert.rejects(() => s.connectLink({ siteId: "s1", platform: "linkedin" }), (err) => err.code === "not_supported");
});

test("connect link provisions the account once and records it in Meelu", async () => {
  const adapter = new FakeAdapter();
  const meelu = fakeMeelu();
  const s = scheduler({ adapters: [adapter], connected: ["fake"], meelu });
  const link = await s.connectLink({ siteId: "s1", platform: "linkedin", redirectUrl: "https://app/back" });
  assert.equal(link.url, "https://vendor/connect/linkedin");
  assert.deepEqual(meelu.state.account, { id: "acc_1", provider: "fake", externalAccountId: "grp_1" });
  await s.connectLink({ siteId: "s1", platform: "bluesky" });
  assert.equal(adapter.calls.filter(([c]) => c === "createAccount").length, 1);
});

test("scheduling a piece creates the post and marks the piece scheduled", async () => {
  const adapter = new FakeAdapter();
  const meelu = fakeMeelu({
    account: { id: "acc_1", provider: "fake", externalAccountId: "grp_1" },
    pieces: { pc1: { id: "pc1", status: "draft", mediaSource: "none", channelKey: "linkedin", scheduledAt: null } },
  });
  const s = scheduler({ adapters: [adapter], connected: ["fake"], meelu });
  const out = await s.schedulePost({
    siteId: "s1",
    pieceId: "pc1",
    body: "hello",
    profiles: ["linkedin"],
    scheduledAt: "2026-10-01T15:30:00.000Z",
  });
  assert.equal(out.post.id, "post_1");
  assert.equal(meelu.state.pieces.pc1.status, "scheduled");
  assert.equal(meelu.state.pieces.pc1.externalPostId, "post_1");
  await assert.rejects(
    () => s.schedulePost({ siteId: "s1", pieceId: "pc1", body: "again", profiles: ["linkedin"] }),
    /already scheduled/,
  );
});

test("scheduling to a platform that is not connected is refused before the vendor is called", async () => {
  const adapter = new FakeAdapter();
  const meelu = fakeMeelu({ account: { id: "acc_1", provider: "fake", externalAccountId: "grp_1" } });
  const s = scheduler({ adapters: [adapter], connected: ["fake"], meelu });
  await assert.rejects(() => s.schedulePost({ siteId: "s1", body: "x", profiles: ["bluesky"] }), /isn't connected/);
  assert.ok(!adapter.calls.some(([c]) => c === "createPost"));
});

test("reschedule floors to the hour in the channel timezone and cancel returns the piece to draft", async () => {
  const adapter = new FakeAdapter();
  adapter.posts.set("post_9", { id: "post_9", status: "scheduled", scheduledAt: "2026-10-01T15:00:00.000Z", platforms: [] });
  const meelu = fakeMeelu({
    account: { id: "acc_1", provider: "fake", externalAccountId: "grp_1" },
    pieces: {
      pc9: { id: "pc9", status: "scheduled", externalPostId: "post_9", channelKey: "linkedin", scheduledAt: "2026-10-01T15:00:00.000Z" },
    },
  });
  const s = scheduler({ adapters: [adapter], connected: ["fake"], meelu });
  await s.reschedule({ siteId: "s1", pieceId: "pc9", scheduledAt: "2026-10-01T15:45:00.000Z" });
  const patch = adapter.calls.find(([c]) => c === "updatePost")[3];
  assert.equal(patch.scheduledAt, "2026-10-01T15:00:00.000Z");
  const piece = await s.cancelSchedule({ siteId: "s1", pieceId: "pc9" });
  assert.equal(piece.status, "draft");
  assert.equal(piece.externalPostId, null);
});

test("reconcile marks published pieces posted", async () => {
  const adapter = new FakeAdapter();
  adapter.posts.set("post_2", {
    id: "post_2",
    status: "processed",
    scheduledAt: null,
    platforms: [{ platform: "linkedin", status: "published", url: "https://li/1", error: null }],
  });
  const meelu = fakeMeelu({
    account: { id: "acc_1", provider: "fake", externalAccountId: "grp_1" },
    pieces: { pc2: { id: "pc2", status: "scheduled", externalPostId: "post_2", channelKey: "linkedin" } },
  });
  const s = scheduler({ adapters: [adapter], connected: ["fake"], meelu });
  const out = await s.reconcile({ siteId: "s1", pieceIds: ["pc2"] });
  assert.equal(out.reconciled, 1);
  assert.equal(meelu.state.pieces.pc2.status, "posted");
  assert.equal(meelu.state.pieces.pc2.postedUrl, "https://li/1");
});
