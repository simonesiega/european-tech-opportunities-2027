# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS internships

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Cache Python dependencies independently from application source.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY configs ./configs
COPY src ./src

RUN uv sync --frozen --no-dev \
    && groupadd --gid 10001 internships \
    && useradd \
        --uid 10001 \
        --gid internships \
        --home-dir /app \
        --no-create-home \
        --shell /usr/sbin/nologin \
        internships \
    && mkdir -p /app/data /workspace \
    && chown -R internships:internships /app /workspace

USER internships
ENTRYPOINT ["uv", "run", "--no-sync", "internships"]
CMD ["--help"]


FROM oven/bun:1.3.14-alpine@sha256:5acc90a93e91ff07bf72aa90a7c9f0fa189765aec90b47bdbf2152d2196383c0 AS site-deps
WORKDIR /app
COPY site/package.json site/bun.lock ./
RUN bun install --frozen-lockfile


FROM node:26-alpine@sha256:725aeba2364a9b16beae49e180d83bd597dbd0b15c47f1f28875c290bfd255b9 AS site-builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG SITE_URL=https://internship2027.simonesiega.com
ENV SITE_URL=$SITE_URL
COPY --from=site-deps /usr/local/bin/bun /usr/local/bin/bun
COPY --from=site-deps /app/node_modules ./node_modules
COPY site ./
RUN bun run build


FROM node:26-alpine@sha256:725aeba2364a9b16beae49e180d83bd597dbd0b15c47f1f28875c290bfd255b9 AS site
WORKDIR /app

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    SITE_URL=https://internship2027.simonesiega.com \
    INTERNSHIPS_DATABASE_PATH=/app/data/internships.db

RUN addgroup --system --gid 10001 nodejs \
    && adduser --system --uid 10001 --ingroup nodejs nextjs \
    && mkdir -p /app/data \
    && chown nextjs:nodejs /app/data

COPY --from=site-builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=site-builder --chown=nextjs:nodejs /app/.next/static ./.next/static

EXPOSE 3000
USER nextjs
CMD ["node", "server.js"]
