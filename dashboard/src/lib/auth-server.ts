import "server-only";

import { betterAuth, type BetterAuthOptions } from "better-auth";
import { APIError, createAuthMiddleware } from "better-auth/api";
import { nextCookies } from "better-auth/next-js";
import { emailOTP, jwt, signJWT, type JwtOptions } from "better-auth/plugins";
import { Pool } from "pg";

const OTP_SECONDS = 600;
const SENDER = "Meelu <noreply@meelu.tech>";
const API = process.env.MEELU_API_URL ?? "http://localhost:8100";
const PASSWORD_CHANGES = new Set(["/email-otp/reset-password", "/change-password"]);

type OtpType = "sign-in" | "email-verification" | "forget-password" | "change-email";

const OTP_EMAILS: Partial<Record<OtpType, { subject: string; lead: string }>> = {
  "email-verification": {
    subject: "Your Meelu verification code",
    lead: "Use this code to confirm your email address for Meelu:",
  },
  "forget-password": {
    subject: "Your Meelu password reset code",
    lead: "Use this code to set a new password for Meelu:",
  },
};

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is not set.`);
  return value;
}

async function sendOtpEmail(email: string, otp: string, type: OtpType): Promise<void> {
  const template = OTP_EMAILS[type];
  if (!template) return;
  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    if (process.env.NODE_ENV === "production") throw new Error("RESEND_API_KEY is not set.");
    console.info(`[auth] ${type} code for ${email}: ${otp}`);
    return;
  }
  const minutes = OTP_SECONDS / 60;
  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${apiKey}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: SENDER,
      to: [email],
      subject: template.subject,
      text: `${template.lead}\n\n${otp}\n\nIt expires in ${minutes} minutes. If you did not ask for it, ignore this email.\n\nMeelu`,
    }),
  });
  if (!res.ok) throw new Error(`Resend refused the ${type} email: ${res.status} ${await res.text()}`);
}

function buildOptions() {
  const baseURL = required("BETTER_AUTH_URL");
  const pool = new Pool({ connectionString: required("AUTH_DATABASE_URL"), max: 5 });
  const jwtOptions = {
    disableSettingJwtHeader: true,
    jwks: { keyPairConfig: { alg: "EdDSA", crv: "Ed25519" } },
    jwt: {
      issuer: baseURL,
      audience: baseURL,
      expirationTime: "5m",
      definePayload: ({ user }) => ({
        email: user.email,
        emailVerified: user.emailVerified,
        name: user.name,
      }),
    },
  } satisfies JwtOptions;

  return {
    appName: "Meelu",
    baseURL,
    basePath: "/auth",
    secret: required("BETTER_AUTH_SECRET"),
    trustedOrigins: [baseURL],
    database: pool,
    disabledPaths: [
      "/sign-in/email-otp",
      "/forget-password/email-otp",
      "/email-otp/request-email-change",
      "/email-otp/change-email",
      "/request-password-reset",
      "/reset-password",
    ],
    emailAndPassword: {
      enabled: true,
      minPasswordLength: 8,
      requireEmailVerification: true,
      revokeSessionsOnPasswordReset: true,
    },
    emailVerification: {
      sendOnSignIn: true,
      autoSignInAfterVerification: true,
    },
    session: {
      expiresIn: 60 * 10,
      updateAge: 60 * 10,
    },
    rateLimit: {
      enabled: true,
      storage: "memory",
      window: 60,
      max: 60,
      customRules: {
        "/sign-in/email": { window: 60, max: 5 },
        "/sign-up/email": { window: 600, max: 5 },
        "/email-otp/send-verification-otp": { window: 300, max: 4 },
        "/email-otp/verify-email": { window: 300, max: 10 },
        "/email-otp/request-password-reset": { window: 300, max: 3 },
        "/email-otp/reset-password": { window: 300, max: 10 },
      },
    },
    advanced: {
      useSecureCookies: baseURL.startsWith("https://"),
      ipAddress: { ipAddressHeaders: ["cf-connecting-ip"] },
    },
    hooks: {
      before: createAuthMiddleware(async (ctx) => {
        if (ctx.path !== "/sign-up/email") return;
        const email = typeof ctx.body?.email === "string" ? ctx.body.email.toLowerCase() : "";
        if (!email) return;
        const existing = await ctx.context.internalAdapter.findUserByEmail(email);
        if (!existing) return;
        if (existing.user.emailVerified) {
          throw new APIError("UNPROCESSABLE_ENTITY", {
            code: "USER_ALREADY_EXISTS",
            message: "An account with this email already exists. Sign in instead.",
          });
        }
        await ctx.context.internalAdapter.deleteUser(existing.user.id);
      }),
      after: createAuthMiddleware(async (ctx) => {
        if (!PASSWORD_CHANGES.has(ctx.path)) return;
        const returned = ctx.context.returned;
        if (!returned || returned instanceof Error) return;
        const email = typeof ctx.body?.email === "string" ? ctx.body.email.toLowerCase() : "";
        const user =
          ctx.context.session?.user ??
          (email ? (await ctx.context.internalAdapter.findUserByEmail(email))?.user : undefined);
        if (!user) return;
        const accessToken = await signJWT(ctx, {
          options: jwtOptions,
          payload: { sub: user.id, email: user.email, emailVerified: true },
        });
        const res = await fetch(`${API}/api/auth/sessions/revoke`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ accessToken }),
        });
        if (!res.ok) console.error(`[auth] api kept sessions for ${user.id} after a password change: ${res.status}`);
      }),
    },
    plugins: [
      emailOTP({
        otpLength: 6,
        expiresIn: OTP_SECONDS,
        allowedAttempts: 3,
        storeOTP: "hashed",
        disableSignUp: true,
        sendVerificationOnSignUp: true,
        overrideDefaultEmailVerification: true,
        async sendVerificationOTP({ email, otp, type }) {
          await sendOtpEmail(email, otp, type);
        },
      }),
      jwt(jwtOptions),
      nextCookies(),
    ],
  } satisfies BetterAuthOptions;
}

let options: ReturnType<typeof buildOptions> | undefined;

export function authOptions(): ReturnType<typeof buildOptions> {
  options ??= buildOptions();
  return options;
}

function buildInstance() {
  return betterAuth(authOptions());
}

let instance: ReturnType<typeof buildInstance> | undefined;

export function authServer(): ReturnType<typeof buildInstance> {
  instance ??= buildInstance();
  return instance;
}
