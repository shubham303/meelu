# Meelu dashboard — Next.js 16 (App Router) production image.
# Three stages so the runtime layer carries no source, no build tools and no
# dev dependencies: deps → builder → runner.
#
# Debian slim rather than alpine: sharp's prebuilt binaries are linked against
# glibc, and on musl they fail to load at require() time.

# ---- deps: install exactly what the lockfile pins -------------------------
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder: next build, emitting .next/standalone ----------------------
FROM node:22-slim AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG MEELU_API_URL=http://api:8000
ENV MEELU_API_URL=$MEELU_API_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---- runner: standalone server only --------------------------------------
FROM node:22-slim AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN groupadd -g 1001 nodejs && useradd -u 1001 -g nodejs -m nextjs

# standalone bundles server.js + the traced subset of node_modules. `public`
# and `.next/static` are not copied into it by the build, so bring them over
# ourselves — server.js serves them once they are in place.
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# sharp ships platform-specific native binaries that the standalone tracer
# copies as JavaScript only, so bring the installed trees over whole.
COPY --from=deps --chown=nextjs:nodejs /app/node_modules/sharp ./node_modules/sharp
COPY --from=deps --chown=nextjs:nodejs /app/node_modules/@img ./node_modules/@img

USER nextjs
EXPOSE 3000

# Landing page is public, so a 200 there means the server is really serving.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=5 \
  CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
