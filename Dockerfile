# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Cache third-party dependencies independently from source changes.
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