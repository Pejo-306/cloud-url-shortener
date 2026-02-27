# Backend

Python backend for CloudShortener (API Gateway + Lambda). 

Local dev environment uses `uv` for dependency management, `Ruff` for linting/formatting,
`ty` for type checking, `pytest` for tests. AWS lambdas use a uv-produced `requirements.txt`.

You can manage the backend via the [backend Makefile](./Makefile).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.13+

## Application Configuration

Backend configuration is stored and managed by *AWS AppConfig* when `cloudshortener` is deployed in AWS.

For local development an *AWS AppConfig Agent* is instead used to store backend configuration. 
Check [local README](../local/README.md) for more details.

## Targets

Run from the `backend/` directory:

| Target                 | Description                                  |
|------------------------|----------------------------------------------|
| `make install`         | Create/sync uv venv                          |
| `make clean`           | Remove .venv, caches                         |
| `make code-check`      | Run lint, format-diff, ty (safe, no changes)  |
| `make unittests`       | Run unit tests                               |
| `make integration-tests` | Run integration tests                      |
| `make tests`           | Run unit and integration tests                |
| `make coverage`        | Run pytest with coverage                      |
| `make build`           | Build requirements.txt for AWS Lambdas       |

For other local development targets, inspect `make help`.

## Usage

Local day-to-day development looks like:

1. `make install` to install all dependencies (create/sync uv venv)
2. Run tests with `make unittests` (or `make tests` for unit + integration). Inspect `make help` for coverage and test options
3. Run a code-check with `make code-check` and inspect `make help` for targets to fix any linting/formatting/typing
4. Deploy a local development server. Check [local README](../local/README.md) for details.
5. `make build` to produce requirements.txt for AWS Lambda deployment
