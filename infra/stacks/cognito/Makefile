# infra/stacks/cognito/Makefile
# Run from infra/stacks/cognito/: make deploy, make destroy
# Or from infra/: make deploy-cognito (orchestrator delegates here)

# AWS SAM configuration
# WARNING: do not edit these files manually, they are managed by AWS SAM.
SAM_CONFIG                := ../../../samconfig.toml
TEMPLATE                  := template.yaml
CAPABILITIES              ?= CAPABILITY_IAM
S3_BUCKET                 ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

# Configurable AWS stack variables
STACK_NAME                ?= cloudshortener-cognito-dev
APP_NAME                  ?= cloudshortener
APP_ENV                   ?= dev
AWS_REGION                ?= eu-central-1
AWS_PROFILE               ?= personal-dev

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: build deploy destroy help

help:
	@echo "Cognito stack - Authorizes shortening requests to cloudshortener's backend"
	@echo ""
	@echo "Deploys Cognito User Pool and User Pool Client for authentication. Used by the"
	@echo "backend API Gateway authorizer to authorize shortening requests."
	@echo "Also used for authentication flow in our frontend. No dependencies."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make deploy                               - Deploy Cognito stack"
	@echo "  make destroy                              - Destroy Cognito stack"
	@echo "  make help                                 - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  STACK_NAME                                - CloudFormation stack name"
	@echo "  APP_NAME                                  - Application name"
	@echo "  APP_ENV                                   - Environment (dev, staging, prod)"
	@echo "  AWS_REGION                                - AWS region"
	@echo "  AWS_PROFILE                               - AWS profile"
	@echo ""

build:
	@echo "No build needed for cognito stack"

deploy:
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
			AppName=$(APP_NAME)

destroy:
	$(call confirm_destroy,$(STACK_NAME))
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts
