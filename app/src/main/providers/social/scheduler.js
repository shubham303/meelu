import { z } from "zod";
import { ENV_DEFAULTS } from "../../config.js";
import { ProviderError, ProviderRequestError } from "../errors.js";
import { ProviderFacade } from "../registry.js";
import { defineTools } from "../tools.js";

const RECONCILE_CAP = 50;

export class SchedulerConflict extends ProviderError {
  constructor(message) {
    super("conflict", message);
  }
}

function activePlatforms(profiles) {
  return new Set(profiles.filter((p) => p.status === "active").map((p) => p.platform));
}

function hourFloor(instant, timeZone) {
  const at = new Date(instant);
  if (Number.isNaN(at.getTime())) throw new SchedulerConflict("scheduledAt must be a valid ISO date-time.");
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone,
    hourCycle: "h23",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).formatToParts(at);
  const get = (type) => Number(parts.find((p) => p.type === type)?.value);
  const asUtc = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour"), get("minute"), get("second"));
  const offsetMs = asUtc - at.getTime();
  const flooredLocal = Date.UTC(get("year"), get("month") - 1, get("day"), get("hour"), 0, 0);
  return new Date(flooredLocal - offsetMs).toISOString();
}

function remoteInstant(value) {
  if (!value) return null;
  const at = new Date(value);
  return Number.isNaN(at.getTime()) ? null : at.toISOString();
}

function sameInstant(a, b) {
  if (!a || !b) return false;
  return new Date(a).getTime() === new Date(b).getTime();
}

function describe(err) {
  if (err instanceof ProviderRequestError) {
    if (err.status === 401 || err.status === 403) {
      return new SchedulerConflict(`${err.providerId} refused the API key. Check it on the Connections screen.`);
    }
    if (err.status === 429) return new SchedulerConflict(`${err.providerId} is rate-limiting this key. Try again shortly.`);
    if (err.status == null) return new SchedulerConflict(`Could not reach ${err.providerId}. Check the connection and try again.`);
    const detail =
      (typeof err.body === "object" && err.body && (err.body.error?.message ?? err.body.error ?? err.body.message)) || "";
    return new ProviderRequestError(
      err.providerId,
      err.status,
      `${err.providerId} request failed (${err.status})${detail ? `: ${detail}` : "."}`,
      err.body,
    );
  }
  return err;
}

function isClientError(err) {
  return err instanceof ProviderRequestError && err.status != null && err.status >= 400 && err.status < 500;
}

export class SocialMediaScheduler extends ProviderFacade {
  constructor(opts) {
    super({ domain: "social", label: "social publishing", ...opts });
  }

  api(path, { siteId, ...rest } = {}) {
    return this.meelu.request(path, { siteId, ...rest });
  }

  async account(siteId) {
    return this.api("/social/account", { siteId, allow: [404] });
  }

  async adapterFor(siteId, capability, provider = null) {
    const account = await this.account(siteId);
    const adapter = this.require(capability, provider ?? account?.provider ?? null);
    if (account && account.provider !== adapter.id) {
      throw new SchedulerConflict(
        `This website's social accounts live on ${account.provider}, but ${adapter.id} was asked. ` +
          "Disconnect one or name the other provider.",
      );
    }
    return { adapter, account };
  }

  async ensureAccount(siteId, provider = null) {
    const { adapter, account } = await this.adapterFor(siteId, "accounts.create", provider);
    if (account) return { adapter, account };
    const site = await this.api("/site", { siteId });
    const name = site?.name ? `${site.name} (${site.domain})` : siteId;
    let created;
    try {
      created = await adapter.createAccount(name);
    } catch (err) {
      throw describe(err);
    }
    const saved = await this.api("/social/account", {
      siteId,
      method: "PUT",
      body: { provider: adapter.id, externalAccountId: created.id },
    });
    return { adapter, account: saved };
  }

  async listProfiles(adapter, account) {
    try {
      return await adapter.listProfiles(account.externalAccountId);
    } catch (err) {
      throw describe(err);
    }
  }

  async patchPiece(siteId, pieceId, body) {
    return this.api(`/content/pieces/${encodeURIComponent(pieceId)}`, {
      siteId,
      method: "PATCH",
      body,
      actor: "system",
    });
  }

  async piece(siteId, pieceId) {
    return this.api(`/content/pieces/${encodeURIComponent(pieceId)}`, { siteId });
  }

  async profiles({ siteId, provider = null }) {
    const account = await this.account(siteId);
    const connected = this.connectedAdapters();
    if (!account && connected.length === 0) {
      await this.api("/social/channels/sync", { siteId, method: "POST", body: { platforms: [] } });
      return { provider: null, accountConnected: false, profiles: [], platforms: [] };
    }
    const { adapter } = await this.adapterFor(siteId, "profiles.list", provider);
    if (!account) {
      return { provider: adapter.id, accountConnected: false, profiles: [], platforms: adapter.constructor.platforms };
    }
    const profiles = await this.listProfiles(adapter, account);
    await this.api("/social/channels/sync", {
      siteId,
      method: "POST",
      body: { platforms: [...activePlatforms(profiles)] },
    });
    return { provider: adapter.id, accountConnected: true, profiles, platforms: adapter.constructor.platforms };
  }

  async connectLink({ siteId, platform, redirectUrl = null, provider = null }) {
    const { adapter, account } = await this.ensureAccount(siteId, provider);
    if (!adapter.constructor.platforms.includes(platform)) {
      throw new SchedulerConflict(
        `${adapter.name} cannot connect ${platform}. It supports: ${adapter.constructor.platforms.join(", ")}.`,
      );
    }
    const backTo =
      redirectUrl && redirectUrl.startsWith(ENV_DEFAULTS.meeluBaseUrl)
        ? redirectUrl
        : `${ENV_DEFAULTS.meeluBaseUrl}/dashboard/connections?social=connected`;
    try {
      return await adapter.connectLink(account.externalAccountId, platform, backTo);
    } catch (err) {
      throw describe(err);
    }
  }

  async disconnectProfile({ siteId, profileId }) {
    const { adapter, account } = await this.adapterFor(siteId, "profiles.disconnect");
    if (!account) throw new SchedulerConflict("This website has no social account yet.");
    const profiles = await this.listProfiles(adapter, account);
    if (!profiles.some((p) => p.id === profileId)) {
      throw new SchedulerConflict("That account isn't connected to this website.");
    }
    try {
      await adapter.disconnectProfile(account.externalAccountId, profileId);
    } catch (err) {
      throw describe(err);
    }
    await this.profiles({ siteId });
    return { disconnected: true };
  }

  async resolveMedia(siteId, piece) {
    if (piece.mediaSource === "unsplash" && piece.mediaUrl) return { urls: [piece.mediaUrl], files: [] };
    if (piece.mediaSource === "upload" && piece.mediaUploadId) {
      let media;
      try {
        media = await this.meelu.bytes(`/content/media/${encodeURIComponent(piece.mediaUploadId)}`, { siteId });
      } catch {
        throw new SchedulerConflict(
          "This post's image is missing from the workspace — re-attach it before publishing.",
        );
      }
      const ext = (media.contentType.split("/")[1] ?? "").replace(/[^a-zA-Z0-9]/g, "") || "jpg";
      return {
        urls: [],
        files: [{ filename: `meelu-${piece.id}.${ext}`, contentType: media.contentType, data: media.data }],
      };
    }
    return { urls: [], files: [] };
  }

  async schedulePost({ siteId, pieceId = null, body, profiles, mediaUrls = [], scheduledAt = null }) {
    if (!Array.isArray(profiles) || profiles.length === 0) {
      throw new SchedulerConflict("profiles is required: platform names or profile ids from the connected accounts.");
    }
    for (const url of mediaUrls) {
      if (!/^https?:\/\//.test(url)) {
        throw new SchedulerConflict("Every mediaUrls entry must be a public http(s) URL.");
      }
    }
    const { adapter, account } = await this.adapterFor(siteId, "posts.create");
    if (!account) {
      throw new SchedulerConflict(
        "This website has no social accounts connected yet. Connect one on the Channels screen first.",
      );
    }
    const connected = await this.listProfiles(adapter, account);
    const reachable = new Set([
      ...activePlatforms(connected),
      ...connected.filter((p) => p.status === "active").map((p) => p.id),
    ]);
    const missing = profiles.find((p) => !reachable.has(p));
    if (missing) {
      throw new SchedulerConflict(
        `${missing} isn't connected for this website. Connect it on the Channels screen before scheduling.`,
      );
    }

    let piece = null;
    if (pieceId) {
      piece = await this.piece(siteId, pieceId);
      if (piece.status === "scheduled") {
        throw new SchedulerConflict(
          "This post is already scheduled. Reschedule it rather than publishing it twice, or cancel the schedule first.",
        );
      }
      if (piece.status === "posted") throw new SchedulerConflict("This post is already marked posted.");
      if (piece.status === "blocked") {
        throw new SchedulerConflict("This post breaks its channel's limits. Fix the checks on it first.");
      }
      if (scheduledAt) {
        piece = await this.patchPiece(siteId, piece.id, { scheduledAt });
        scheduledAt = piece.scheduledAt;
      }
    }

    const { urls, files } = piece ? await this.resolveMedia(siteId, piece) : { urls: [], files: [] };
    const input = { body, profiles, mediaUrls: [...mediaUrls, ...urls], scheduledAt };
    let post;
    try {
      if (files.length) {
        if (!adapter.capabilities.has("posts.create_with_files")) throw adapter.unsupported("posts.create_with_files");
        post = await adapter.createPostWithFiles(account.externalAccountId, input, files);
      } else {
        post = await adapter.createPost(account.externalAccountId, input);
      }
    } catch (err) {
      throw describe(err);
    }

    if (piece) {
      await this.patchPiece(siteId, piece.id, { status: "scheduled", externalPostId: post.id, failure: null });
    }
    return { provider: adapter.id, post };
  }

  async requireAccount(siteId, capability) {
    const { adapter, account } = await this.adapterFor(siteId, capability);
    if (!account) throw new SchedulerConflict("This website has no social account yet.");
    return { adapter, account };
  }

  async postStatus({ siteId, postId }) {
    const { adapter, account } = await this.requireAccount(siteId, "posts.get");
    try {
      return await adapter.getPost(account.externalAccountId, postId);
    } catch (err) {
      throw describe(err);
    }
  }

  async cancelPost({ siteId, postId }) {
    const { adapter, account } = await this.requireAccount(siteId, "posts.delete");
    try {
      await adapter.deletePost(account.externalAccountId, postId);
    } catch (err) {
      throw describe(err);
    }
    return { canceled: true };
  }

  async cancelSchedule({ siteId, pieceId }) {
    const piece = await this.piece(siteId, pieceId);
    if (piece.status !== "scheduled" || !piece.externalPostId) {
      throw new SchedulerConflict("This post isn't scheduled with a provider.");
    }
    const { adapter, account } = await this.requireAccount(siteId, "posts.delete");
    try {
      await adapter.deletePost(account.externalAccountId, piece.externalPostId);
    } catch (err) {
      if (isClientError(err)) {
        throw new SchedulerConflict(
          `${adapter.name} won't cancel this post — it locks one shortly before its slot, so this one ` +
            "is already going out. Check back in a minute and it will show as posted.",
        );
      }
      throw describe(err);
    }
    return this.patchPiece(siteId, piece.id, { status: "draft", externalPostId: null, failure: null });
  }

  async reschedule({ siteId, pieceId, scheduledAt }) {
    const piece = await this.piece(siteId, pieceId);
    if (!piece.externalPostId) return this.patchPiece(siteId, piece.id, { scheduledAt });
    const channel = await this.api(`/content/channels/${encodeURIComponent(piece.channelKey)}`, { siteId });
    const floored = hourFloor(scheduledAt, channel.timezone);
    const { adapter, account } = await this.requireAccount(siteId, "posts.update");
    try {
      await adapter.updatePost(account.externalAccountId, piece.externalPostId, { scheduledAt: floored });
    } catch (err) {
      if (isClientError(err)) {
        throw new SchedulerConflict(
          `${adapter.name} won't move this post — it locks one shortly before its slot, so this one is ` +
            `already on its way out at ${piece.scheduledAt}. Let it publish, or cancel it if you still can.`,
        );
      }
      throw describe(err);
    }
    return this.patchPiece(siteId, piece.id, { scheduledAt: floored });
  }

  async reconcile({ siteId, pieceIds = [] }) {
    const account = await this.account(siteId);
    if (!account) return { reconciled: 0 };
    let adapter;
    try {
      adapter = this.require("posts.get", account.provider);
    } catch {
      return { reconciled: 0 };
    }

    let candidates = [];
    if (pieceIds.length) {
      for (const id of pieceIds.slice(0, RECONCILE_CAP)) {
        const one = await this.api(`/content/pieces/${encodeURIComponent(id)}`, { siteId, allow: [404] });
        if (one) candidates.push(one);
      }
    } else {
      const page = await this.meelu.request(`/content/pieces?status=scheduled&page_size=${RECONCILE_CAP}`, {
        siteId,
      });
      candidates = Array.isArray(page) ? page : (page?.data ?? []);
    }

    let reconciled = 0;
    for (const piece of candidates) {
      if (piece.status !== "scheduled" || !piece.externalPostId) continue;
      let remote;
      try {
        remote = await adapter.getPost(account.externalAccountId, piece.externalPostId);
      } catch (err) {
        if (err instanceof ProviderRequestError && err.status === 404) {
          await this.patchPiece(siteId, piece.id, {
            status: "draft",
            externalPostId: null,
            failure: `This post is no longer on ${adapter.name} — it was removed there.`,
          }).catch(() => null);
          reconciled += 1;
        }
        continue;
      }
      const published = remote.platforms.find((p) => p.url);
      const failed = remote.platforms.find((p) => p.error);
      try {
        if (remote.status === "processed" || published) {
          await this.patchPiece(siteId, piece.id, {
            status: "posted",
            postedAt: new Date().toISOString(),
            ...(published?.url ? { postedUrl: published.url } : {}),
          });
          reconciled += 1;
        } else if (failed || remote.status === "media_processing_failed") {
          await this.patchPiece(siteId, piece.id, {
            status: "failed",
            externalPostId: null,
            failure: failed?.error ?? `${adapter.name} could not process this post's media.`,
          });
          reconciled += 1;
        } else {
          const remoteAt = remoteInstant(remote.scheduledAt);
          if (remoteAt && !sameInstant(remoteAt, piece.scheduledAt)) {
            await this.patchPiece(siteId, piece.id, { scheduledAt: remoteAt });
            reconciled += 1;
          }
        }
      } catch {
        continue;
      }
    }
    return { reconciled };
  }
}

const site = z.string().describe("Website id");

defineTools(SocialMediaScheduler, [
  {
    name: "social_profiles",
    description:
      "List the social accounts connected for this website through the connected publishing provider. Also refreshes which channels are enabled in Meelu.",
    input: z.object({ siteId: site }),
    method: "profiles",
  },
  {
    name: "social_connect_link",
    description:
      "Get a browser URL that connects one social platform to this website. Hand the URL to the user; the connection completes in their browser.",
    input: z.object({ siteId: site, platform: z.string().describe("Platform key, e.g. linkedin") }),
    method: "connectLink",
  },
  {
    name: "social_disconnect_profile",
    description: "Disconnect one social account from this website.",
    input: z.object({ siteId: site, profileId: z.string() }),
    method: "disconnectProfile",
  },
  {
    name: "social_schedule_post",
    description:
      "Schedule or publish a post to connected accounts and mark the Meelu content piece scheduled. Pass pieceId so the piece's media and status follow; omit scheduledAt to publish now.",
    input: z.object({
      siteId: site,
      pieceId: z.string().nullable().optional(),
      body: z.string(),
      profiles: z.array(z.string()).describe("Platform keys or profile ids"),
      mediaUrls: z.array(z.string()).optional(),
      scheduledAt: z.string().nullable().optional().describe("ISO instant"),
    }),
    method: "schedulePost",
  },
  {
    name: "social_post_status",
    description: "Read a scheduled post's status and per-platform results from the provider.",
    input: z.object({ siteId: site, postId: z.string() }),
    method: "postStatus",
  },
  {
    name: "social_cancel_schedule",
    description: "Cancel a scheduled content piece at the provider and return it to draft in Meelu.",
    input: z.object({ siteId: site, pieceId: z.string() }),
    method: "cancelSchedule",
  },
  {
    name: "social_reschedule",
    description:
      "Move a content piece to a new time, floored to the hour in its channel's timezone, at the provider and in Meelu.",
    input: z.object({ siteId: site, pieceId: z.string(), scheduledAt: z.string().describe("ISO instant") }),
    method: "reschedule",
  },
  {
    name: "social_reconcile",
    description:
      "Sync scheduled pieces with the provider: mark posted, failed or removed ones. Pass pieceIds to limit it.",
    input: z.object({ siteId: site, pieceIds: z.array(z.string()).optional() }),
    method: "reconcile",
  },
]);
