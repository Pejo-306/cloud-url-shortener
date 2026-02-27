# Frontend

Vite-based frontend for CloudShortener. Build, dev server, linting (ESLint), formatting (Prettier), and json-server mock API.

You can manage the frontend via the [frontend Makefile](./Makefile).

## Prerequisites

- [Node.js](https://nodejs.org/) v20+ (LTS)
- [npm](https://www.npmjs.com/) (bundled with Node)

## Targets

Run from the `frontend/` directory:

| Target          | Description                                 |
|-----------------|----------------------------------------------|
| `make install`  | Install npm packages (npm ci)                |
| `make clean`    | Remove node_modules, dist, .eslintcache      |
| `make dev`      | Run Vite dev server                          |
| `make code-check` | Run lint and format-diff (safe, no changes) |
| `make build`    | Build into dist/                             |

For other code quality and local development targets, inspect `make help`.

## Usage

Local day-to-day development looks like:

1. `make install` to install all npm dependencies
2. `make dev` combined with a running json-server or local SAM API. Check config files in `frontend/config/` to configure
3. Run a code-check with `make code-check` and inspect `make help` to fix any linting/formatting
4. `make build` to build into `dist/` and preview with `make preview`
