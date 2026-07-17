.PHONY: install migrate scrape render validate searches stats lint format typecheck test migrations docs check

install:
	uv sync --dev

migrate:
	uv run internships db-upgrade

scrape:
	uv run internships scrape

render:
	uv run internships render

validate:
	uv run internships validate

searches:
	uv run internships searches

stats:
	uv run internships stats

lint:
	uv run ruff format --check .
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src tests scripts

test:
	uv run pytest

migrations:
	uv run python scripts/check_migrations.py

docs:
	uv run python scripts/check_docs.py

check: lint typecheck test migrations docs
