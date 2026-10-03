.PHONY: install lock migrate scrape render validate searches stats lint format typecheck test coverage benchmark test-live migrations docs docs-lint docs-site check

install:
	uv sync --frozen --dev

lock:
	uv lock --check

migrate:
	uv run opportunities db-upgrade

scrape:
	uv run opportunities scrape

render:
	uv run opportunities render

validate:
	uv run opportunities validate

searches:
	uv run opportunities searches

stats:
	uv run opportunities stats

lint:
	uv run ruff format --check .
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests scripts

test:
	uv run pytest -m "not live and not performance"

coverage:
	mkdir -p quality-reports
	uv run pytest -m "not live and not performance" --cov --cov-report=term-missing --cov-report=xml:quality-reports/coverage.xml --cov-report=json:quality-reports/coverage.json --cov-report=html:quality-reports/coverage-html
	uv run python scripts/docs/coverage_docs.py

benchmark:
	mkdir -p quality-reports
	uv run pytest tests/benchmarks --benchmark-only --benchmark-json=quality-reports/benchmark.json

test-live:
	uv run pytest -m "live"

migrations:
	uv run python scripts/database/check_migrations.py

docs:
	uv run python scripts/docs/check_docs.py

docs-lint:
	uv run --frozen python scripts/docs/lint_docs.py

docs-site: docs docs-lint
	uv run --frozen --group docs python scripts/docs/build_docs.py
	uv run --frozen --group docs python scripts/docs/check_built_docs.py

check: lock lint typecheck coverage migrations docs-site
