import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

export class MeeluApi {
  constructor({ cookieHeader = "" } = {}) {
    this.cookieHeader = cookieHeader;
  }

  headers({ siteId, body, actor } = {}) {
    return {
      ...meeluAuthHeaders(this.cookieHeader),
      ...(body !== undefined ? { "content-type": "application/json" } : {}),
      ...(siteId ? { "x-meelu-site": siteId } : {}),
      ...(actor ? { "x-meelu-actor": actor } : {}),
    };
  }

  async request(path, { method = "GET", body, siteId, actor, allow = [] } = {}) {
    const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
      method,
      headers: this.headers({ siteId, body, actor }),
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
    });
    const json = await res.json().catch(() => ({}));
    if (!res.ok && !allow.includes(res.status)) {
      const err = new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
      err.status = res.status;
      throw err;
    }
    if (!res.ok) return null;
    return json?.data ?? json;
  }

  async bytes(path, { siteId } = {}) {
    const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
      headers: this.headers({ siteId }),
    });
    if (!res.ok) throw new Error(`GET ${path} failed (${res.status})`);
    return {
      contentType: res.headers.get("content-type") ?? "application/octet-stream",
      data: new Uint8Array(await res.arrayBuffer()),
    };
  }
}
