# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# Pin every external build image by digest to keep supply-chain inputs reproducible.
FROM ghcr.io/astral-sh/uv:0.12.11@sha256:79c6f4776b851471cc73b7d21d0cc834bb94383c292e83640d27eff512864df7 AS uv

FROM python:3.14.7-slim-trixie@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6 AS opportunities

COPY --from=uv /uv /uvx /usr/local/bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /app

# Install the reviewed Debian security revisions exactly. Version pins keep the
# runtime reproducible while the base-image digest catches up with the archive.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends --only-upgrade \
        gzip=1.13-1+deb13u1 \
        libpcre2-8-0=10.46-1~deb13u2 \
        libsqlite3-0=3.46.1-7+deb13u2 \
        perl-base=5.40.1-6+deb13u1 \
    && rm -rf /var/lib/apt/lists/*

# Cache Python dependencies independently from application source.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY migrations ./migrations
COPY configs ./configs
COPY src ./src

RUN uv sync --frozen --no-dev \
    && rm -rf /usr/local/lib/python*/site-packages/pip* \
    && rm -f /usr/local/bin/pip* /usr/local/bin/uv /usr/local/bin/uvx \
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

# Runtime executes the installed console script without package-manager tooling.
USER 10001:10001
ENTRYPOINT ["/app/.venv/bin/opportunities"]
CMD ["--help"]


# Bun installs locked dependencies in a disposable stage; only build output reaches runtime.
FROM oven/bun:1.4.2-alpine@sha256:d888c0ae6c86d7866ff10c5aafdd9077b36aee6455b33dd270fb93c0dd5cef6f AS site-deps
WORKDIR /app
COPY site/package.json site/bun.lock ./
RUN bun install --frozen-lockfile


FROM node:26-alpine@sha256:ef24c5053d50fdc3e4e56eb4e7ddb7861874ab0fdc797046ba897581deb8e868 AS site-builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
ARG SITE_URL=https://opportunities2027.simonesiega.com
ENV SITE_URL=$SITE_URL
COPY --from=site-deps /usr/local/bin/bun /usr/local/bin/bun
COPY --from=site-deps /app/node_modules ./node_modules
COPY site ./
RUN bun run build


FROM node:26-trixie-slim@sha256:14bf3eac4bf209d906d3c41256597d3ab1f926b2e93a79e9bdfe1efd32454239 AS site
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    SITE_URL=https://opportunities2027.simonesiega.com \
    OPPORTUNITIES_DATABASE_PATH=/app/data/opportunities.db

# Install exact security revisions until they are incorporated into the pinned
# base image, then omit npm because the standalone server does not use it.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends --only-upgrade \
        gzip=1.13-1+deb13u1 \
        libpcre2-8-0=10.46-1~deb13u2 \
        libsqlite3-0=3.46.1-7+deb13u2 \
        perl-base=5.40.1-6+deb13u1 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/local/lib/node_modules/npm \
    && rm -f /usr/local/bin/npm /usr/local/bin/npx \
    && groupadd --system --gid 10001 nodejs \
    && useradd --system --uid 10001 --gid nodejs --home-dir /app --no-create-home nextjs \
    && mkdir -p /app/data \
    && chown nextjs:nodejs /app/data

COPY --from=site-builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=site-builder --chown=nextjs:nodejs /app/.next/static ./.next/static

EXPOSE 3000
USER 10001:10001
CMD ["node", "server.js"]
