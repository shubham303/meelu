import type { NextConfig } from "next";

/**
 * Defense-in-depth behind the analytics HTML validator: srcdoc iframes
 * INHERIT this policy, so even if a network-referencing report slipped past
 * validation, the browser would refuse the request. img-src lists the one
 * external origin the product legitimately renders (Unsplash post media —
 * their guidelines require hotlinking). 'unsafe-eval'/'unsafe-inline' are
 * what Next itself needs (dev refresh, inline bootstrap); they don't weaken
 * the exfiltration story, which is about where requests may GO.
 */
const SUPABASE = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";

const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://images.unsplash.com https://lh3.googleusercontent.com",
  "font-src 'self' data:",
  `connect-src 'self' ${SUPABASE}`.trim(),
  "worker-src 'self' blob:",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

const nextConfig: NextConfig = {
  // Emits .next/standalone — a self-contained server.js plus only the traced
  // node_modules. The Dockerfile copies that instead of the full dependency
  // tree. Harmless outside Docker; `next dev` and `next start` ignore it.
  output: "standalone",
  async rewrites() {
    const api = process.env.MEELU_API_URL ?? "http://localhost:8100";
    return {
      beforeFiles: [
        { source: "/api/auth/:path*", destination: `${api}/api/auth/:path*` },
        { source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [{ key: "Content-Security-Policy", value: CSP }],
      },
    ];
  },
};

export default nextConfig;
