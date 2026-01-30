.PHONY: install
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

.PHONY: unittests
unittests:
	pytest tests/unit

.PHONY: coverage
coverage:
	pytest tests/unit --cov=cloudshortener --cov-report=term-missing --cov-fail-under=80

.PHONY: lint
lint:
	ruff check . --preview

.PHONY: lint-fix
lint-fix:
	ruff check . --preview --fix

.PHONY: format
format:
	ruff format .

.PHONY: format-diff
format-diff:
	ruff format --diff .

.PHONY: code-check
code-check: lint-fix format coverage