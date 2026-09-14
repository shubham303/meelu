import { ProviderRequestError } from "../errors.js";
import { vendorRequest } from "../vendor-http.js";
import { SocialAdapter, SOCIAL_CAPABILITIES } from "./adapter.js";

const PLATFORMS = [
  "facebook",
  "instagram",
  "tiktok",
  "linkedin",
  "youtube",
  "twitter",
  "threads",
  "pinterest",
  "bluesky",
  "telegram",
  "google_business",
];

function pick(data, ...keys) {
  for (const key of keys) {
    const value = data?.[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return null;
}

function profile(row) {
  return {
    id: String(row.id),
    name: String(row.name ?? ""),
    status: String(row.status ?? "active"),
    platform: String(row.platform ?? ""),
    avatarUrl: row.avatar_url ?? null,
  };
}

function post(raw) {
  const rows = Array.isArray(raw?.platforms)
    ? raw.platforms
    : Array.isArray(raw?.platform_posts)
      ? raw.platform_posts
      : [];
  return {
    id: String(raw?.id),
    body: raw?.body == null ? "" : String(raw.body),
    status: raw?.status == null ? "" : String(raw.status),
    scheduledAt: raw?.scheduled_at ?? null,
    platforms: rows
      .filter((r) => r && typeof r === "object")
      .map((r) => ({
        platform: pick(r, "platform", "network", "provider") ?? "",
        status: pick(r, "status", "state") ?? "",
        url: pick(r, "permalink", "url", "post_url", "link"),
        error: pick(r, "error", "error_message", "failure_reason", "message"),
      })),
  };
}

export class PostproxyAdapter extends SocialAdapter {
  static id = "postproxy";
  static name_ = "Postproxy";

  static get capabilities() {
    return new Set(SOCIAL_CAPABILITIES);
  }

  static get platforms() {
    return PLATFORMS;
  }

  baseUrl() {
    return (this.credentials?.baseUrl || "https://api.postproxy.dev").replace(/\/$/, "");
  }

  headers() {
    return { authorization: `Bearer ${this.credentials?.apiKey ?? ""}` };
  }

  call(path, options = {}) {
    return vendorRequest(this.id, `${this.baseUrl()}${path}`, {
      ...options,
      headers: { ...this.headers(), ...(options.headers ?? {}) },
    });
  }

  async createAccount(name) {
    const raw = await this.call("/api/profile_groups", { method: "POST", json: { name } });
    const id = raw?.id ?? raw?.data?.id;
    if (!id) {
      throw new ProviderRequestError(
        this.id,
        502,
        "Postproxy created a profile group without returning its id.",
        raw,
      );
    }
    return { id: String(id) };
  }

  async connectLink(accountId, platform, redirectUrl) {
    const raw = await this.call(
      `/api/profile_groups/${encodeURIComponent(accountId)}/initialize_connection`,
      { method: "POST", json: { platform, redirect_url: redirectUrl } },
    );
    return { url: String(raw?.url ?? ""), expiresAt: raw?.expires_at ?? null };
  }

  async listProfiles(accountId) {
    const raw = await this.call("/api/profiles", {
      query: { profile_group_id: accountId, per_page: 50 },
    });
    const rows = Array.isArray(raw) ? raw : (raw?.data ?? []);
    return rows.map(profile);
  }

  async disconnectProfile(accountId, profileId) {
    void accountId;
    await this.call(`/api/profiles/${encodeURIComponent(profileId)}`, { method: "DELETE" });
  }

  async createPost(accountId, { body, profiles, mediaUrls = [], scheduledAt = null }) {
    const payload = {
      post: { body, ...(scheduledAt ? { scheduled_at: scheduledAt } : {}) },
      profiles,
      profile_group_id: accountId,
      ...(mediaUrls.length ? { media: mediaUrls } : {}),
    };
    return post(await this.call("/api/posts", { method: "POST", json: payload }));
  }

  async createPostWithFiles(accountId, { body, profiles, scheduledAt = null }, files) {
    const fields = {
      "post[body]": body,
      profile_group_id: accountId,
      "profiles[]": profiles,
      ...(scheduledAt ? { "post[scheduled_at]": scheduledAt } : {}),
      "media[]": files,
    };
    return post(await this.call("/api/posts", { method: "POST", form: fields, timeoutMs: 120_000 }));
  }

  async updatePost(accountId, postId, { body, scheduledAt, profiles, mediaUrls } = {}) {
    const inner = {};
    if (body != null) inner.body = body;
    if (scheduledAt != null) inner.scheduled_at = scheduledAt;
    const payload = { profile_group_id: accountId };
    if (Object.keys(inner).length) payload.post = inner;
    if (profiles != null) payload.profiles = profiles;
    if (mediaUrls != null) payload.media = mediaUrls;
    return post(
      await this.call(`/api/posts/${encodeURIComponent(postId)}`, { method: "PATCH", json: payload }),
    );
  }

  async getPost(accountId, postId) {
    return post(
      await this.call(`/api/posts/${encodeURIComponent(postId)}`, {
        query: { profile_group_id: accountId },
      }),
    );
  }

  async deletePost(accountId, postId) {
    await this.call(`/api/posts/${encodeURIComponent(postId)}`, {
      method: "DELETE",
      query: { profile_group_id: accountId },
    });
  }
}
