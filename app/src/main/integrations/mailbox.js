import { resolveMx } from "node:dns/promises";
import { ImapFlow } from "imapflow";
import { simpleParser } from "mailparser";
import { mailboxValuesFor } from "../connector-config.js";

const KNOWN_IMAP_HOSTS = {
  "gmail.com": "imap.gmail.com",
  "googlemail.com": "imap.gmail.com",
  "zoho.com": "imap.zoho.com",
  "zoho.in": "imap.zoho.in",
  "zoho.eu": "imap.zoho.eu",
  "fastmail.com": "imap.fastmail.com",
  "fastmail.fm": "imap.fastmail.com",
  "yahoo.com": "imap.mail.yahoo.com",
  "icloud.com": "imap.mail.me.com",
  "me.com": "imap.mail.me.com",
};

const MX_IMAP_PROVIDERS = [
  { suffix: "google.com", imap: "imap.gmail.com" },
  { suffix: "googlemail.com", imap: "imap.gmail.com" },
  { suffix: "zoho.eu", imap: "imap.zoho.eu" },
  { suffix: "zoho.in", imap: "imap.zoho.in" },
  { suffix: "zoho.com", imap: "imap.zoho.com" },
  { suffix: "messagingengine.com", imap: "imap.fastmail.com" },
  { suffix: "yahoodns.net", imap: "imap.mail.yahoo.com" },
  { suffix: "icloud.com", imap: "imap.mail.me.com" },
];

const MX_REFUSALS = [
  {
    suffix: "outlook.com",
    reason:
      "its mail is hosted on Microsoft 365, and Microsoft retired app-password IMAP — use a mailbox on another provider.",
  },
  {
    suffix: "protonmail.ch",
    reason:
      "its mail is hosted on Proton, which needs the Proton Bridge app — run the Bridge and set the IMAP host on the connection to the Bridge's local address.",
  },
];

const mxCache = new Map();

async function imapHostFromMx(domain) {
  if (mxCache.has(domain)) return mxCache.get(domain);
  let result = null;
  try {
    const records = await resolveMx(domain);
    const best = records
      .filter((r) => r.exchange)
      .sort((a, b) => a.priority - b.priority)
      .map((r) => r.exchange.toLowerCase().replace(/\.$/, ""));
    outer: for (const exchange of best) {
      for (const { suffix, reason } of MX_REFUSALS) {
        if (exchange === suffix || exchange.endsWith(`.${suffix}`)) {
          result = { refusal: reason };
          break outer;
        }
      }
      for (const { suffix, imap } of MX_IMAP_PROVIDERS) {
        if (exchange === suffix || exchange.endsWith(`.${suffix}`)) {
          result = { imap };
          break outer;
        }
      }
    }
  } catch {
    result = null;
  }
  mxCache.set(domain, result);
  return result;
}

const IDLE_CLOSE_MS = 4 * 60 * 1000;

async function imapConfig(address_ = null) {
  const values = mailboxValuesFor(address_);
  if (values == null) {
    return {
      error: address_
        ? `This website sends as ${address_}, but that mailbox is not connected on this device — connect it on the Connections screen, or change the website's sending address.`
        : "No mailbox connected for this website — connect one, or pick an existing account, on the Connections screen.",
    };
  }
  const address = (values.address ?? "").trim().toLowerCase();
  const password = (values.password ?? "").trim().replace(/\s+/g, "");
  if (!address || !password) {
    return {
      error:
        "The mailbox connection is missing its address or app password — reconnect it on the Connections screen.",
    };
  }
  const domain = address.split("@")[1] ?? "";
  let host = (values.imapHost ?? "").trim() || KNOWN_IMAP_HOSTS[domain];
  if (!host) {
    const detected = await imapHostFromMx(domain);
    if (detected?.refusal) {
      return { error: `Can't connect "${domain}" — ${detected.refusal}` };
    }
    host = detected?.imap;
  }
  if (!host) {
    return {
      error:
        `Couldn't work out the IMAP host for "${domain}" (its MX records don't name ` +
        "a provider I know) — set the IMAP host on the mailbox connection.",
    };
  }
  return { address, password, host };
}

let warm = null;

function connectionKey(cfg) {
  return `${cfg.address}\u0000${cfg.host}\u0000${cfg.password}`;
}

function dropWarm() {
  if (!warm) return;
  clearTimeout(warm.idleTimer);
  const { client } = warm;
  warm = null;
  client.logout().catch(() => client.close());
}

function touchWarm() {
  if (!warm) return;
  clearTimeout(warm.idleTimer);
  warm.idleTimer = setTimeout(dropWarm, IDLE_CLOSE_MS);
}

async function getClient(cfg) {
  const key = connectionKey(cfg);
  if (warm && (warm.key !== key || !warm.client.usable)) dropWarm();
  if (!warm) {
    const client = new ImapFlow({
      host: cfg.host,
      port: 993,
      secure: true,
      auth: { user: cfg.address, pass: cfg.password },
      logger: false,
    });
    client.on("close", () => {
      if (warm?.client === client) {
        clearTimeout(warm.idleTimer);
        warm = null;
      }
    });
    await client.connect();
    warm = { client, key, idleTimer: null };
  }
  touchWarm();
  return warm.client;
}

async function withInbox(fn, address = null) {
  const cfg = await imapConfig(address);
  if (cfg.error) return { error: cfg.error };

  for (let attempt = 0; ; attempt += 1) {
    let client;
    try {
      client = await getClient(cfg);
    } catch (err) {
      const detail = err?.responseText || err?.message || String(err);
      return {
        error: err?.authenticationFailed
          ? `The mailbox refused the login (${detail}). The password must be an APP password — update the connection on the Connections screen.`
          : `Could not reach ${cfg.host}: ${detail}`,
      };
    }
    try {
      const lock = await client.getMailboxLock("INBOX");
      try {
        return await fn(client, cfg);
      } finally {
        lock.release();
      }
    } catch (err) {
      dropWarm();
      if (attempt === 0) continue;
      return {
        error: `Mailbox read failed: ${err?.responseText || err?.message || String(err)}`,
      };
    }
  }
}

export function warmupMailbox() {
  void imapConfig()
    .then((cfg) => (cfg.error ? null : getClient(cfg)))
    .catch(() => {});
}

function addressLine(list) {
  if (!list?.length) return null;
  return list
    .map((a) => (a.name ? `${a.name} <${a.address ?? ""}>` : (a.address ?? "")))
    .join(", ");
}

export async function listInbox({ page = 1, pageSize = 25, address = null } = {}) {
  const p = Math.max(1, Math.floor(page));
  const size = Math.min(100, Math.max(1, Math.floor(pageSize)));
  return withInbox(async (client, cfg) => {
    const total = client.mailbox.exists ?? 0;
    const end = total - (p - 1) * size;
    const start = Math.max(1, end - size + 1);
    const messages = [];
    if (end >= 1) {
      for await (const msg of client.fetch(`${start}:${end}`, {
        uid: true,
        envelope: true,
        flags: true,
      })) {
        const env = msg.envelope;
        messages.push({
          uid: msg.uid,
          seq: msg.seq,
          date: env?.date ? new Date(env.date).toISOString() : null,
          from: addressLine(env?.from),
          subject: env?.subject ?? null,
          seen: msg.flags?.has("\\Seen") ?? false,
        });
      }
      messages.sort((a, b) => b.seq - a.seq);
    }
    return {
      address: cfg.address,
      total,
      page: p,
      pageSize: size,
      pages: Math.max(1, Math.ceil(total / size)),
      messages: messages.map(({ seq: _seq, ...m }) => m),
    };
  }, address);
}

export async function sendMessage({ to, subject, body, replyToMessageId, address = null } = {}) {
  const recipients = (Array.isArray(to) ? to : [to]).map((a) => String(a ?? "").trim()).filter(Boolean);
  if (recipients.length === 0) return { error: "No recipient address." };
  if (!String(subject ?? "").trim()) return { error: "The message needs a subject." };
  if (!String(body ?? "").trim()) return { error: "The message is empty." };

  const cfg = await imapConfig(address);
  if (cfg.error) return { error: cfg.error };

  const values = mailboxValuesFor(address) ?? {};
  const host = (values.smtpHost ?? "").trim() || cfg.host.replace(/^imap\./, "smtp.");

  try {
    const { default: nodemailer } = await import("nodemailer");
    const transporter = nodemailer.createTransport({
      host,
      port: 465,
      secure: true,
      auth: { user: cfg.address, pass: cfg.password },
    });
    const info = await transporter.sendMail({
      from: cfg.address,
      to: recipients,
      subject,
      text: body,
      ...(replyToMessageId
        ? { inReplyTo: `<${replyToMessageId}>`, references: `<${replyToMessageId}>` }
        : {}),
    });
    if (info.rejected?.length) {
      return {
        error: `The mail server rejected ${info.rejected.join(", ")}${
          info.accepted?.length ? ` (accepted ${info.accepted.join(", ")})` : ""
        }.`,
      };
    }
    return {
      messageId: stripAngles(info.messageId),
      from: cfg.address,
      accepted: info.accepted ?? recipients,
      sentAt: new Date().toISOString(),
    };
  } catch (err) {
    const detail = err?.response || err?.message || String(err);
    return {
      error: err?.code === "EAUTH"
        ? `The mail server refused the login (${detail}). The password must be an APP password — update the connection on the Connections screen.`
        : `Could not send via ${host}: ${detail}`,
    };
  }
}

const SYNC_BODY_MAX = 50_000;

export async function syncProspectMessages({ since, prospects = [], address = null } = {}) {
  const from = since ? new Date(since) : null;
  if (!from || Number.isNaN(from.getTime())) return { error: "syncProspectMessages needs a valid `since` date." };

  const byAddress = new Map();
  for (const p of prospects) {
    if (p?.email && p?.id) byAddress.set(String(p.email).trim().toLowerCase(), p.id);
  }
  if (byAddress.size === 0) return { messages: [], scanned: 0, since: from.toISOString() };

  return withInbox(async (client) => {
    const uids = await client.search({ since: from }, { uid: true });
    if (!uids?.length) return { messages: [], scanned: 0, since: from.toISOString() };

    const matched = [];
    for await (const msg of client.fetch(
      uids,
      { uid: true, envelope: true },
      { uid: true },
    )) {
      const env = msg.envelope;
      const sender = env?.from?.[0]?.address?.trim().toLowerCase();
      const prospectId = sender ? byAddress.get(sender) : undefined;
      if (!prospectId) continue;

      const messageId = stripAngles(env?.messageId);
      if (!messageId) continue;

      matched.push({ uid: msg.uid, env, prospectId, messageId });
    }

    const messages = [];
    for (const { uid, env, prospectId, messageId } of matched) {
      const occurredAt = (env?.date ? new Date(env.date) : new Date()).toISOString();
      let subject = env?.subject ?? null;
      let sender = addressLine(env?.from);
      let recipient = addressLine(env?.to);
      let body = "";
      try {
        const download = await client.download(String(uid), undefined, { uid: true });
        if (download?.content) {
          const parsed = await simpleParser(download.content);
          subject = parsed.subject ?? subject;
          sender = parsed.from?.text ?? sender;
          body = (parsed.text ?? "").trim().slice(0, SYNC_BODY_MAX);
        }
      } catch {
      }
      messages.push({
        prospectId,
        messageId,
        threadRef: stripAngles(env?.inReplyTo) || null,
        from: sender,
        to: recipient,
        subject,
        body,
        occurredAt,
      });
    }
    return { messages, scanned: uids.length, since: from.toISOString() };
  }, address);
}

function stripAngles(raw) {
  return typeof raw === "string" ? raw.trim().replace(/^<|>$/g, "") : "";
}

export async function readMessage({ uid, address = null } = {}) {
  const id = Math.floor(Number(uid));
  if (!Number.isInteger(id) || id < 1) return { error: "Invalid message uid." };
  return withInbox(async (client) => {
    const download = await client.download(String(id), undefined, { uid: true });
    if (!download?.content) return { error: `No message with uid ${id} in the inbox.` };
    const parsed = await simpleParser(download.content);
    const body = (parsed.text ?? "").trim();
    const TRUNCATE = 50_000;
    return {
      uid: id,
      date: parsed.date?.toISOString() ?? null,
      from: parsed.from?.text ?? null,
      to: parsed.to
        ? (Array.isArray(parsed.to) ? parsed.to : [parsed.to]).map((t) => t.text).join(", ")
        : null,
      subject: parsed.subject ?? null,
      attachments: parsed.attachments.map((a) => ({
        filename: a.filename ?? "(unnamed)",
        size: a.size,
      })),
      body: body.length > TRUNCATE ? `${body.slice(0, TRUNCATE)}\n…(truncated)` : body,
    };
  }, address);
}
