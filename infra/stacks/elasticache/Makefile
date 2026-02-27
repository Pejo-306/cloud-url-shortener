# infra/stacks/elasticache/Makefile
# Run from infra/stacks/elasticache/: make deploy, make destroy (requires CACHE_SUBNET_GROUP_NAME, ELASTICACHE_SECURITY_GROUP_ID)
# Or from infra/: make deploy-elasticache (orchestrator delegates here)

# AWS SAM configuration
# WARNING: do not edit these files manually, they are managed by AWS SAM.
SAM_CONFIG                    := ../../../samconfig.toml
TEMPLATE                      := template.yaml
CAPABILITIES                  ?= CAPABILITY_IAM
S3_BUCKET                     ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

# Configurable AWS stack variables
STACK_NAME                    ?= cloudshortener-elasticache-dev
APP_NAME                      ?= cloudshortener
APP_ENV                       ?= dev
AWS_REGION                    ?= eu-central-1
AWS_PROFILE                   ?= personal-dev

# Network stack dependencies - required to deploy the ElastiCache stack
CACHE_SUBNET_GROUP_NAME       ?=
ELASTICACHE_SECURITY_GROUP_ID ?=

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: build deploy destroy help

help:
	@echo "ElastiCache stack - Cache layer for cloudshortener's backend"
	@echo ""
	@echo "Deploys Redis replication group (Multi-AZ) for caching and data storage."
	@echo "Used by the backend to cache configuration and data speed up the application."
	@echo "No dependencies."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make deploy                               - Deploy ElastiCache stack"
	@echo "  make destroy                              - Destroy ElastiCache stack"
	@echo "  make help                                 - Show this message"
	@echo ""
	@echo "\033[1mDependencies:\033[0m (from Network stack outputs, required for deploy)"
	@echo "  CACHE_SUBNET_GROUP_NAME                   - ElastiCache subnet group name"
	@echo "  ELASTICACHE_SECURITY_GROUP_ID             - Security group ID for ElastiCache"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  STACK_NAME                                - CloudFormation stack name"
	@echo "  APP_NAME                                  - Application name"
	@echo "  APP_ENV                                   - Environment (dev, staging, prod)"
	@echo "  AWS_REGION                                - AWS region"
	@echo "  AWS_PROFILE                               - AWS profile"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  make deploy CACHE_SUBNET_GROUP_NAME=xxx ELASTICACHE_SECURITY_GROUP_ID=sg-xxx"
	@echo ""

build:
	@echo "No build needed for elasticache stack"

deploy:
	@if [ -z "$(CACHE_SUBNET_GROUP_NAME)" ] || [ -z "$(ELASTICACHE_SECURITY_GROUP_ID)" ]; then \
		echo "ERROR: CACHE_SUBNET_GROUP_NAME and ELASTICACHE_SECURITY_GROUP_ID are required."; \
		echo ""; \
		echo "Example:"; \
		echo "	make deploy CACHE_SUBNET_GROUP_NAME=my-cache-subnet ELASTICACHE_SECURITY_GROUP_ID=sg-xxx"; \
		echo ""; \
		echo "Get these from the Network stack outputs after deploying it."; \
		exit 1; \
	fi
	sam deploy \
		--config-file $(SAM_CONFIG) \
		--template-file $(TEMPLATE) \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--capabilities $(CAPABILITIES) \
		--s3-bucket $(S3_BUCKET) \
		--parameter-overrides \
			AppEnv=$(APP_ENV) \
			AppName=$(APP_NAME) \
			CacheSubnetGroupName=$(CACHE_SUBNET_GROUP_NAME) \
			SecurityGroupId=$(ELASTICACHE_SECURITY_GROUP_ID)

destroy:
	$(call confirm_destroy,$(STACK_NAME))
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts
