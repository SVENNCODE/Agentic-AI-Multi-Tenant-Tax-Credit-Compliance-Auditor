# ai-audit-agent/Dockerfile
# Next.js 16 production image, multi-stage so the final image only ships
# the standalone server output, not the full node_modules/build cache.
#
# Requires next.config.ts to set `output: "standalone"` (already set).

FROM node:22-alpine AS base
WORKDIR /app

# ---- deps: install once, cached separately from source changes ----
FROM base AS deps
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder: compile the app ----
FROM base AS builder
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Public env vars needed at build time (Next.js inlines NEXT_PUBLIC_* at
# build, not at container start). Pass these with --build-arg or compose's
# `args:`; they are not secrets -- they're the same values the browser sees.
ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=$NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# ---- runner: minimal runtime image ----
FROM base AS runner
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# `next build` with output:"standalone" produces a self-contained server
# bundle plus the assets it needs -- copy just those, not the source tree.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME="0.0.0.0"

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:3000/login').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
