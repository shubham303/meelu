import crypto from "node:crypto";
import http from "node:http";
import { shell } from "electron";
import { GSC_OAUTH_CLIENT } from "../../config.js";

const AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SCOPE = "https://www.googleapis.com/auth/webmasters.readonly";

const TIMEOUT_MS = 120_000;

function donePage(heading, detail) {
  return (
    `<!doctype html><meta charset="utf-8"><title>Meelu</title>` +
    `<body style="font:16px/1.5 system-ui;padding:3rem;max-width:32rem;margin:auto;color:#111">` +
    `<h1 style="font-size:1.25rem;margin:0 0 .5rem">${heading}</h1>` +
    `<p style="margin:0;color:#555">${detail}</p></body>`
  );
}

export async function connectSearchConsole() {
  const { clientId, clientSecret } = GSC_OAUTH_CLIENT;
  if (!clientId || !clientSecret) {
    throw new Error(
      "This build has no Google OAuth client configured, so Search Console can't be " +
        "connected. Please reinstall or update the app.",
    );
  }

  const verifier = crypto.randomBytes(32).toString("base64url");
  const challenge = crypto.createHash("sha256").update(verifier).digest("base64url");
  const state = crypto.randomBytes(16).toString("base64url");

  return new Promise((resolve, reject) => {
    let settled = false;
    const server = http.createServer();

    const finish = (fn, value) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      server.close();
      fn(value);
    };

    const timer = setTimeout(
      () => finish(reject, new Error("The Google sign-in timed out. Try connecting again.")),
      TIMEOUT_MS,
    );

    server.on("request", (req, res) => {
      const url = new URL(req.url ?? "/", "http://127.0.0.1");
      if (url.pathname !== "/callback") {
        res.writeHead(404).end();
        return;
      }

      const reply = (status, heading, detail) =>
        res
          .writeHead(status, { "content-type": "text/html; charset=utf-8" })
          .end(donePage(heading, detail));

      const error = url.searchParams.get("error");
      if (error) {
        reply(400, "Authorisation declined.", "Nothing was connected. You can close this tab.");
        finish(reject, new Error(`Google returned "${error}".`));
        return;
      }
      if (url.searchParams.get("state") !== state) {
        reply(400, "That didn't match.", "The callback came from a different request.");
        finish(reject, new Error("State mismatch — the callback did not come from this attempt."));
        return;
      }
      const code = url.searchParams.get("code");
      if (!code) {
        reply(400, "No authorisation code.", "Google's callback carried nothing to exchange.");
        finish(reject, new Error("Google's callback carried no authorisation code."));
        return;
      }

      const { port } = server.address();
      exchange(code, verifier, clientId, clientSecret, port).then(
        (refreshToken) => {
          reply(200, "Search Console connected.", "You can close this tab and go back to Meelu.");
          finish(resolve, { refreshToken, clientId, clientSecret });
        },
        (err) => {
          reply(500, "Couldn't finish connecting.", "Go back to Meelu and try again.");
          finish(reject, err);
        },
      );
    });

    server.on("error", (err) => finish(reject, err));

    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      const params = new URLSearchParams({
        client_id: clientId,
        redirect_uri: `http://127.0.0.1:${port}/callback`,
        response_type: "code",
        scope: SCOPE,
        code_challenge: challenge,
        code_challenge_method: "S256",
        state,
        access_type: "offline",
        prompt: "consent select_account",
      });
      shell.openExternal(`${AUTH_URL}?${params}`).catch((err) => finish(reject, err));
    });
  });
}

async function exchange(code, verifier, clientId, clientSecret, port) {
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: clientId,
      client_secret: clientSecret,
      code_verifier: verifier,
      redirect_uri: `http://127.0.0.1:${port}/callback`,
      grant_type: "authorization_code",
    }),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(payload.error_description ?? payload.error ?? `Google returned ${res.status}.`);
  }
  if (!payload.refresh_token) {
    throw new Error(
      "Google returned no refresh token. This happens when the account already granted " +
        "this app: revoke it at myaccount.google.com/permissions, then connect again.",
    );
  }
  return payload.refresh_token;
}
