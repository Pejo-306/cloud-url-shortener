# Root Makefile - CloudShortener tooling
# Run from repository root. Delegates to backend/, frontend/, local/, infra/, infra/bootstrap/.

# Primary configurable variables (pass-through to infra and sub-makes)
APP_NAME           ?= cloudshortener
APP_ENV            ?= dev
LOG_LEVEL          ?= INFO
AWS_REGION         ?= eu-central-1
AWS_PROFILE        ?= personal-dev
ORCHESTRATOR_STACK ?= $(APP_NAME)-$(APP_ENV)

# Recipe-specific (not documented in help)
## OIDC stack
EXISTING_OIDC_PROVIDER_ARN ?=
## Local SAM invoke
FUNCTION                  ?=
EVENT_FILE                ?=
## Deploy (required for pre-deploy seeding)
ELASTICACHE_PASSWORD      ?=

# Local Docker Compose stack ports
REDIS_PORT                ?= 6379
REDISINSIGHT_PORT         ?= 5540
APPCONFIG_AGENT_PORT      ?= 2772
LOCALSTACK_EDGE_PORT      ?= 4566
LOCALSTACK_AUX_PORT       ?= 4571

.PHONY: help install clean code-check up down dev invoke bootstrap build deploy destroy pre-deploy post-deploy

help:
	@echo "CloudShortener tooling"
	@echo ""
	@echo "\033[1mLocal development:\033[0m"
	@echo "  make install                             		   - Install backend + frontend dependencies"
	@echo "  make clean                               		   - Clean backend + frontend"
	@echo "  make code-check                          		   - Run code-check (backend + frontend)"
	@echo "  make up                                  		   - Start local Docker Compose stack"
	@echo "  make down                                		   - Stop local Docker Compose stack"
	@echo "  make dev                                 		   - Start local SAM API + Vite dev server"
	@echo "  make invoke FUNCTION=<name> EVENT_FILE=<path>     - Invoke Lambda locally"
	@echo ""
	@echo "\033[1mDeployment to AWS:\033[0m"
	@echo "  make bootstrap                           		   - Deploy OIDC stack (GitHub Actions)"
	@echo "  make build                               		   - Build backend + frontend + infra"
	@echo "  make deploy ELASTICACHE_PASSWORD='...'   		   - Deploy orchestrator stack (ELASTICACHE_PASSWORD required)"
	@echo "  make destroy                             		   - Destroy orchestrator stack"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make <target> VAR=value)"
	@echo "  APP_NAME                                 		   - Application name"
	@echo "  APP_ENV                                  		   - Environment (dev, staging, prod)"
	@echo "  LOG_LEVEL                                		   - Logging level (DEBUG, INFO, etc.)"
	@echo "  AWS_REGION                               		   - AWS region"
	@echo "  AWS_PROFILE                              		   - AWS profile"
	@echo ""
	@echo "\033[1mUsage examples:\033[0m"
	@echo "  make install                             		   # setup local development environment"
	@echo "  make dev                                          # start SAM API + Vite dev server (requires make build first)"
	@echo "  make bootstrap EXISTING_OIDC_PROVIDER_ARN=arn:aws:iam::123456789012:oidc-provider/..."
	@echo "  export ELASTICACHE_PASSWORD='...' & make deploy   # deploy orchestrator stack (ELASTICACHE_PASSWORD required)"
	@echo "  make destroy                             		   # destroy orchestrator stack"
	@echo ""
	@echo "Run from repository root. For subdirectory targets, run make from backend/, frontend/, local/, infra/, or infra/bootstrap/."

install:
	$(MAKE) -C backend install
	$(MAKE) -C frontend install

clean:
	$(MAKE) -C backend clean
	$(MAKE) -C frontend clean

code-check:
	$(MAKE) -C backend code-check
	$(MAKE) -C frontend code-check

up:
	$(MAKE) -C local up \
		REDIS_PORT="$(REDIS_PORT)" \
		REDISINSIGHT_PORT="$(REDISINSIGHT_PORT)" \
		APPCONFIG_AGENT_PORT="$(APPCONFIG_AGENT_PORT)" \
		LOCALSTACK_EDGE_PORT="$(LOCALSTACK_EDGE_PORT)" \
		LOCALSTACK_AUX_PORT="$(LOCALSTACK_AUX_PORT)"

down:
	$(MAKE) -C local down \
		REDIS_PORT="$(REDIS_PORT)" \
		REDISINSIGHT_PORT="$(REDISINSIGHT_PORT)" \
		APPCONFIG_AGENT_PORT="$(APPCONFIG_AGENT_PORT)" \
		LOCALSTACK_EDGE_PORT="$(LOCALSTACK_EDGE_PORT)" \
		LOCALSTACK_AUX_PORT="$(LOCALSTACK_AUX_PORT)"

dev:
	$(MAKE) -C infra local-api \
		APP_NAME="$(APP_NAME)" APP_ENV="$(APP_ENV)" LOG_LEVEL="$(LOG_LEVEL)" \
		AWS_REGION="$(AWS_REGION)" AWS_PROFILE="$(AWS_PROFILE)" & \
	$(MAKE) -C frontend dev & \
	wait

invoke:
	$(MAKE) -C infra invoke \
		FUNCTION="$(FUNCTION)" EVENT_FILE="$(abspath $(EVENT_FILE))" \
		AWS_PROFILE="$(AWS_PROFILE)"

bootstrap:
	$(MAKE) -C infra/bootstrap oidc-up EXISTING_OIDC_PROVIDER_ARN="$(EXISTING_OIDC_PROVIDER_ARN)"

build:
	$(MAKE) -C backend build
	$(MAKE) -C frontend build
	$(MAKE) -C infra build \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		LOG_LEVEL="$(LOG_LEVEL)" \
		AWS_REGION="$(AWS_REGION)" \
		AWS_PROFILE="$(AWS_PROFILE)"


pre-deploy:
	$(MAKE) -C infra/bootstrap seed-ssm \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		AWS_PROFILE="$(AWS_PROFILE)"
	$(MAKE) -C infra/bootstrap seed-secrets \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		AWS_PROFILE="$(AWS_PROFILE)"
	$(MAKE) -C infra/bootstrap seed-elasticache-secrets \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		ELASTICACHE_PASSWORD="$(ELASTICACHE_PASSWORD)" \
		AWS_PROFILE="$(AWS_PROFILE)"

post-deploy:
	@ENDPOINT=$$(aws cloudformation describe-stacks \
		--stack-name $(ORCHESTRATOR_STACK) \
		--query 'Stacks[0].Outputs[?OutputKey==`ElastiCachePrimaryEndpoint`].OutputValue' \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)); \
	HOST=$$(echo "$$ENDPOINT" | cut -d: -f1); \
	PORT=$$(echo "$$ENDPOINT" | cut -d: -f2); \
	$(MAKE) -C infra/bootstrap seed-elasticache-ssm \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		ELASTICACHE_HOST="$$HOST" \
		ELASTICACHE_PORT="$$PORT" \
		AWS_PROFILE="$(AWS_PROFILE)"

deploy: build
	@if [ -z "$(ELASTICACHE_PASSWORD)" ]; then \
		echo "ERROR: ELASTICACHE_PASSWORD is required for deploy."; \
		echo ""; \
		echo "Example: make deploy ELASTICACHE_PASSWORD='your-redis-password'"; \
		exit 1; \
	fi
	$(MAKE) pre-deploy
	$(MAKE) -C infra deploy \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		LOG_LEVEL="$(LOG_LEVEL)" \
		AWS_REGION="$(AWS_REGION)" \
		AWS_PROFILE="$(AWS_PROFILE)"
	$(MAKE) post-deploy

destroy:
	$(MAKE) -C infra destroy \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		AWS_REGION="$(AWS_REGION)" \
		AWS_PROFILE="$(AWS_PROFILE)"
