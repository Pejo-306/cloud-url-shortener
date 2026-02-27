# Configurable variables (override via: make build MODE=dev)
MODE				?= dev
JSON_SERVER_PORT	?= 3000
VITE_PORT			?= 5173
PREVIEW_PORT		?= 4173

.PHONY: install clean dev preview lint lint-fix format format-diff code-check build json-server help

help:
	@echo "Frontend build and development"
	@echo ""
	@echo "\033[1mSetup:\033[0m"
	@echo "  make install                             # installs npm packages"
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make install                             - Install npm packages (npm ci)"
	@echo "  make clean                               - Remove node_modules, dist, .eslintcache (asks for confirmation)"
	@echo "  make dev                                 - Run Vite dev server"
	@echo "  make preview                             - Run Vite preview (serves dist/)"
	@echo "  make lint                                - ESLint check only"
	@echo "  make lint-fix                            - ESLint with --fix"
	@echo "  make format                              - Prettier write"
	@echo "  make format-diff                         - Prettier check"
	@echo "  make code-check                          - Run lint and format-diff (safe, no changes)"
	@echo "  make build                               - Build into dist/"
	@echo "  make json-server                         - Run json-server mock API"
	@echo "  make help                                - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make build MODE=dev)"
	@echo "  MODE                                     - Vite build mode (dev, staging, prod; 'local' not valid for build)"
	@echo "  JSON_SERVER_PORT                         - json-server port"
	@echo "  VITE_PORT                                - Vite dev server port"
	@echo "  PREVIEW_PORT                             - Vite preview port"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  make build MODE=dev                      # builds the application with dev configuration"
	@echo "  make json-server JSON_SERVER_PORT=4000   # runs json-server on port 4000"
	@echo "  make dev VITE_PORT=8080                  # runs dev server on port 8080"

install:
	npm ci

clean:
	@echo "This will remove node_modules, dist, and .eslintcache. Continue? [y/N]"
	@read -r confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] && rm -rf node_modules dist .eslintcache || (echo "Aborted." && exit 0)

dev:
	npm run dev -- --port $(VITE_PORT)

preview:
	npm run preview -- --port $(PREVIEW_PORT)

lint:
	npm run lint

lint-fix:
	npm run lint-fix

format:
	npm run format

format-diff:
	npm run format-diff

code-check: lint format-diff

build:
	npm run build -- --mode $(MODE)

json-server:
	JSON_SERVER_PORT=$(JSON_SERVER_PORT) npm run json-server
