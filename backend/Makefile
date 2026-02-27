# Configurable variables (override via: make coverage TEST_DIR=tests/)
TEST_DIR	   ?= tests/unit/
COV_FAIL_UNDER ?= 80

.PHONY: help install clean lint lint-fix format format-diff ty unittests integration-tests tests coverage code-check build

help:
	@echo "Backend Python build and development"
	@echo ""
	@echo "\033[1mSetup:\033[0m"
	@echo "  make install                             # creates/syncs uv venv"
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make install                             - Create/sync uv venv"
	@echo "  make clean                               - Remove .venv, caches (asks for confirmation)"
	@echo "  make lint                                - Ruff check only"
	@echo "  make lint-fix                            - Ruff check with --fix"
	@echo "  make format                              - Ruff format write"
	@echo "  make format-diff                         - Ruff format check"
	@echo "  make ty                                  - Ty type check"
	@echo "  make unittests                           - Run unit tests"
	@echo "  make integration-tests                   - Run integration tests"
	@echo "  make tests                               - Run unit and integration tests"
	@echo "  make coverage                            - Run pytest with coverage"
	@echo "  make code-check                          - Run lint, format-diff, ty (safe, no changes)"
	@echo "  make build                               - Build requirements.txt for AWS Lambdas"
	@echo "  make help                                - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make coverage TEST_DIR=tests/)"
	@echo "  TEST_DIR                                 - Test directory for coverage (default: tests/unit/)"
	@echo "  COV_FAIL_UNDER                           - Minimum coverage percentage (default: 80)"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  make coverage TEST_DIR=tests/            # run coverage on full test suite"
	@echo "  make coverage COV_FAIL_UNDER=90          # require 90%% coverage"
	@echo "  make build                               # build requirements.txt"

install:
	uv sync

clean:
	@echo "This will remove .venv, .ruff_cache, __pycache__, .pytest_cache, .coverage, htmlcov. Continue? [y/N]"
	@read -r confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] && (rm -rf .venv .ruff_cache .pytest_cache .coverage .coverage.* htmlcov; find . -depth -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true) || (echo "Aborted." && exit 0)

lint:
	uv run ruff check . --preview

lint-fix:
	uv run ruff check . --preview --fix

format:
	uv run ruff format .

format-diff:
	uv run ruff format --diff .

ty:
	uv run ty check .

unittests:
	uv run pytest tests/unit

integration-tests:
	uv run pytest tests/integration/

tests: unittests integration-tests

coverage:
	uv run pytest $(TEST_DIR) --cov=cloudshortener --cov-report=term-missing --cov-fail-under=$(COV_FAIL_UNDER)

code-check: lint format-diff ty

build:
	uv export --no-dev --no-hashes --format requirements.txt --no-emit-project -o requirements.txt
