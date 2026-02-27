# infra/Makefile - Orchestrator for AWS SAM stacks
# Run from infra/: make deploy, make deploy-backend, etc.
# Run from infra/stacks/backend/: make deploy, make build, etc.

# Deployment config (override via: make deploy AWS_PROFILE=prod-profile)
APP_NAME           ?= cloudshortener
APP_ENV            ?= dev
LOG_LEVEL          ?= INFO
AWS_REGION         ?= eu-central-1
AWS_PROFILE        ?= personal-dev
S3_BUCKET          ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

ORCHESTRATOR_STACK ?= $(APP_NAME)-$(APP_ENV)
BACKEND_DIR        ?= stacks/backend

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: build deploy destroy pre-destroy help local-api invoke
.PHONY: build-network deploy-network destroy-network
.PHONY: build-cognito deploy-cognito destroy-cognito
.PHONY: build-appconfig deploy-appconfig destroy-appconfig
.PHONY: build-frontend deploy-frontend sync-frontend destroy-frontend
.PHONY: build-elasticache deploy-elasticache destroy-elasticache
.PHONY: build-backend deploy-backend destroy-backend

help:
	@echo "AWS SAM infrastructure - Orchestrator for CloudShortener's AWS SAM stacks."
	@echo ""
	@echo "Orchestrator deploys the full CloudShortener stack:"
	@echo "  - Network (VPC, subnets, security groups)"
	@echo "  - Cognito (auth)"
	@echo "  - AppConfig (config)"
	@echo "  - Frontend (S3 + CloudFront)"
	@echo "  - ElastiCache (Redis)"
	@echo "  - Backend (API Gateway + Lambda)"
	@echo ""
	@echo "\033[1mOrchestrator (full stack):\033[0m"
	@echo "  make build                                - Build orchestrator template"
	@echo "  make deploy                               - Deploy entire stack (builds frontend, runs sync)"
	@echo "  make destroy                              - Destroy entire stack"
	@echo ""
	@echo "\033[1mStandalone stacks:\033[0m (from infra/)"
	@echo "  make deploy-network                      - VPC, subnets, security groups (no deps)"
	@echo "  make deploy-cognito                      - User Pool + Client (no deps)"
	@echo "  make deploy-appconfig                    - AppConfig app/env/profile (no deps)"
	@echo "  make deploy-frontend                     - S3 + CloudFront (no deps)"
	@echo "  make sync-frontend                       - Sync frontend/dist/ to S3 and invalidate CloudFront"
	@echo "  make deploy-elasticache                  - Redis (requires CACHE_SUBNET_GROUP_NAME, ELASTICACHE_SECURITY_GROUP_ID)"
	@echo "  make deploy-backend                      - API Gateway + Lambda (requires Network/Cognito/AppConfig outputs)"
	@echo "  make destroy-<stack>                     - Destroy specific stack"
	@echo "  make build-<stack>                       - Build specific stack"
	@echo ""
	@echo "\033[1mLocal development:\033[0m"
	@echo "  make local-api                           - sam local start-api"
	@echo "  make invoke FUNCTION=<name>              - sam local invoke"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  APP_NAME                                 - Application name"
	@echo "  APP_ENV                                  - Environment (dev, staging, prod)"
	@echo "  LOG_LEVEL                                - Logging level (DEBUG, INFO, etc.)"
	@echo "  AWS_REGION                               - AWS region"
	@echo "  AWS_PROFILE                              - AWS profile"
	@echo "  S3_BUCKET                                - S3 bucket for SAM artifacts"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  make deploy                              # Deploy full stack tree"
	@echo "  make sync-frontend                       # Sync new frontend changes to AWS stack"
	@echo "  make deploy-elasticache \                # Deploy just the ElastiCache stack"
	@echo "    CACHE_SUBNET_GROUP_NAME=xxx \\"
	@echo "    ELASTICACHE_SECURITY_GROUP_ID=sg-xxx"
	@echo "  make invoke \                            # Invoke ShortenUrlFunction in a local Docker container"
	@echo "    FUNCTION=ShortenUrlFunction \\"
	@echo "    EVENT_FILE=../events/shorten_url/event.json"
	@echo "  make local-api                           # Start local dev SAM api in Docker containers"
	@echo ""

# Delegation to stack Makefiles (no include to avoid target override warnings)
deploy-network:; $(MAKE) -C stacks/network deploy
build-network:; $(MAKE) -C stacks/network build
destroy-network:; $(MAKE) -C stacks/network destroy

deploy-cognito:; $(MAKE) -C stacks/cognito deploy
build-cognito:; $(MAKE) -C stacks/cognito build
destroy-cognito:; $(MAKE) -C stacks/cognito destroy

deploy-appconfig:; $(MAKE) -C stacks/appconfig deploy
build-appconfig:; $(MAKE) -C stacks/appconfig build
destroy-appconfig:; $(MAKE) -C stacks/appconfig destroy

deploy-frontend:; $(MAKE) -C stacks/frontend deploy
sync-frontend:; $(MAKE) -C stacks/frontend sync STACK_NAME=$(ORCHESTRATOR_STACK)
build-frontend:; $(MAKE) -C stacks/frontend build
destroy-frontend:; $(MAKE) -C stacks/frontend destroy

deploy-elasticache:
	@if [ -z "$(CACHE_SUBNET_GROUP_NAME)" ] || [ -z "$(ELASTICACHE_SECURITY_GROUP_ID)" ]; then \
		echo "ERROR: CACHE_SUBNET_GROUP_NAME and ELASTICACHE_SECURITY_GROUP_ID are required."; \
		echo ""; \
		echo "Example:"; \
		echo "	make deploy-elasticache CACHE_SUBNET_GROUP_NAME=my-cache-subnet ELASTICACHE_SECURITY_GROUP_ID=sg-xxx"; \
		echo ""; \
		echo "Get these from the Network stack outputs after deploying it."; \
		exit 1; \
	fi
	$(MAKE) -C stacks/elasticache deploy CACHE_SUBNET_GROUP_NAME="$(CACHE_SUBNET_GROUP_NAME)" ELASTICACHE_SECURITY_GROUP_ID="$(ELASTICACHE_SECURITY_GROUP_ID)"
build-elasticache:; $(MAKE) -C stacks/elasticache build
destroy-elasticache:; $(MAKE) -C stacks/elasticache destroy

deploy-backend:
	@if [ -z "$(PRIVATE_SUBNET_A)" ] || [ -z "$(PRIVATE_SUBNET_B)" ] || [ -z "$(LAMBDA_SECURITY_GROUP_ID)" ] || \
		[ -z "$(USER_POOL_ID)" ] || [ -z "$(USER_POOL_ARN)" ] || [ -z "$(USER_POOL_CLIENT_ID)" ] || \
		[ -z "$(APPCONFIG_APPLICATION_ID)" ] || [ -z "$(APPCONFIG_ENVIRONMENT_ID)" ] || [ -z "$(BACKEND_CONFIG_PROFILE_ID)" ]; then \
		echo "ERROR: deploy-backend requires parameters from Network, Cognito, and AppConfig stacks."; \
		echo ""; \
		echo "Required: PRIVATE_SUBNET_A, PRIVATE_SUBNET_B, LAMBDA_SECURITY_GROUP_ID,"; \
		echo "  USER_POOL_ID, USER_POOL_ARN, USER_POOL_CLIENT_ID,"; \
		echo "  APPCONFIG_APPLICATION_ID, APPCONFIG_ENVIRONMENT_ID, BACKEND_CONFIG_PROFILE_ID"; \
		echo ""; \
		echo "Get these from the stack outputs after deploying Network, Cognito, AppConfig."; \
		exit 1; \
	fi
	$(MAKE) -C stacks/backend deploy \
		PRIVATE_SUBNET_A="$(PRIVATE_SUBNET_A)" \
		PRIVATE_SUBNET_B="$(PRIVATE_SUBNET_B)" \
		LAMBDA_SECURITY_GROUP_ID="$(LAMBDA_SECURITY_GROUP_ID)" \
		USER_POOL_ID="$(USER_POOL_ID)" \
		USER_POOL_ARN="$(USER_POOL_ARN)" \
		USER_POOL_CLIENT_ID="$(USER_POOL_CLIENT_ID)" \
		APPCONFIG_APPLICATION_ID="$(APPCONFIG_APPLICATION_ID)" \
		APPCONFIG_ENVIRONMENT_ID="$(APPCONFIG_ENVIRONMENT_ID)" \
		BACKEND_CONFIG_PROFILE_ID="$(BACKEND_CONFIG_PROFILE_ID)"
build-backend:; $(MAKE) -C stacks/backend build
destroy-backend:; $(MAKE) -C stacks/backend destroy

# Orchestrator targets (full stack) - samconfig at project root
SAM_CONFIG   := ../samconfig.toml
TEMPLATE     := template.yaml
CAPABILITIES ?= CAPABILITY_IAM CAPABILITY_AUTO_EXPAND

build:
	sam build \
		--config-file $(SAM_CONFIG) \
		-t $(TEMPLATE) \
		--use-container

deploy: build build-frontend
	sam deploy \
		--config-file $(SAM_CONFIG) \
		--stack-name $(ORCHESTRATOR_STACK) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--capabilities $(CAPABILITIES) \
		--s3-bucket $(S3_BUCKET) \
		--parameter-overrides \
			AppEnv=$(APP_ENV) \
			AppName=$(APP_NAME) \
			LogLevel=$(LOG_LEVEL)
	$(MAKE) -C stacks/frontend sync STACK_NAME=$(ORCHESTRATOR_STACK)

pre-destroy:
	$(MAKE) -C stacks/appconfig pre-destroy STACK_NAME=$(ORCHESTRATOR_STACK)
	$(MAKE) -C stacks/frontend pre-destroy STACK_NAME=$(ORCHESTRATOR_STACK)

destroy:
	$(call confirm_destroy,$(ORCHESTRATOR_STACK))
	$(MAKE) pre-destroy
	sam delete \
		--stack-name $(ORCHESTRATOR_STACK) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts

# Local development
ENV_FILE         ?= env.local.json
DOCKER_NETWORK   ?= cloudshortener_local-net

local-api:
	# NOTE: make sure to run `make build` before this target
	sam local start-api \
		--profile $(AWS_PROFILE) \
		--env-vars $(ENV_FILE) \
		--docker-network $(DOCKER_NETWORK) \
		--warm-containers EAGER

invoke:
ifndef FUNCTION
	$(error FUNCTION is required. Example: make invoke FUNCTION=ShortenUrlFunction EVENT_FILE=../events/shorten_url/event.json)
endif
ifndef EVENT_FILE
	$(error EVENT_FILE is required. Example: make invoke FUNCTION=ShortenUrlFunction EVENT_FILE=../events/shorten_url/event.json)
endif
	# NOTE: make sure to run `make build` before this target
	sam local invoke $(FUNCTION) \
		--profile $(AWS_PROFILE) \
		--event $(abspath $(EVENT_FILE)) \
		--env-vars $(ENV_FILE) \
		--docker-network $(DOCKER_NETWORK)
