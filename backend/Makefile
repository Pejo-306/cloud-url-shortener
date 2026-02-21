.PHONY: install
install:
	uv sync

.PHONY: unittests
unittests:
	uv run pytest tests/unit

.PHONY: coverage
coverage:
	uv run pytest tests/unit --cov=cloudshortener --cov-report=term-missing --cov-fail-under=80

.PHONY: lint
lint:
	uv run ruff check . --preview

.PHONY: lint-fix
lint-fix:
	uv run ruff check . --preview --fix

.PHONY: format
format:
	uv run ruff format .

.PHONY: format-diff
format-diff:
	uv run ruff format --diff .

.PHONY: ty
ty:
	uv run ty check .

.PHONY: export-requirements
export-requirements:
	uv export --no-dev --no-hashes --format requirements.txt --no-emit-project -o requirements.txt

.PHONY: code-check
code-check: lint format-diff ty coverage