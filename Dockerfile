# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.31@sha256:ecd4de2f060c64bea0ff8ecb182ddf46ba3fcccdc8a60cfdbaf20d1a047d7437 AS uv

FROM python:3.14.6-slim-bookworm@sha256:86f975aca15cf04a40b399eebede9aea7c82eae084d1f1a0a6ef6bcaae871a30 AS opportunities

COPY --from=uv /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app

# Cache Python dependencies independently from application source.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY configs ./configs
COPY src ./src

RUN uv sync --frozen --no-dev \
    && groupadd --gid 10001 opportunities \
    && useradd \
        --uid 10001 \
        --gid opportunities \
        --home-dir /app \
        --no-create-home \
        --shell /usr/sbin/nologin \
        opportunities \
    && mkdir -p /app/data /workspace \
    && chown -R opportunities:opportunities /app /workspace

USER opportunities
ENTRYPOINT ["uv", "run", "--no-sync", "opportunities"]
CMD ["--help"]


FROM oven/bun:1.3.14-alpine@sha256:5acc90a93e91ff07bf72aa90a7c9f0fa189765aec90b47bdbf2152d2196383c0 AS site-deps
WORKDIR /app
COPY site/package.json site/bun.lock ./
RUN bun install --frozen-lockfile


FROM node:26-alpine@sha256:725aeba2364a9b16beae49e180d83bd597dbd0b15c47f1f28875c290bfd255b9 AS site-builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG SITE_URL=https://opportunities2027.simonesiega.com
ENV SITE_URL=$SITE_URL
COPY --from=site-deps /usr/local/bin/bun /usr/local/bin/bun
COPY --from=site-deps /app/node_modules ./node_modules
COPY site ./
RUN bun run build


FROM node:26-alpine@sha256:725aeba2364a9b16beae49e180d83bd597dbd0b15c47f1f28875c290bfd255b9 AS site
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    SITE_URL=https://opportunities2027.simonesiega.com \
    OPPORTUNITIES_DATABASE_PATH=/app/data/opportunities.db

RUN addgroup --system --gid 10001 nodejs \
    && adduser --system --uid 10001 --ingroup nodejs nextjs \
    && mkdir -p /app/data \
    && chown nextjs:nodejs /app/data

COPY --from=site-builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=site-builder --chown=nextjs:nodejs /app/.next/static ./.next/static

EXPOSE 3000
USER nextjs
CMD ["node", "server.js"]
