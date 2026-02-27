# infra/stacks/appconfig/Makefile
# Run from infra/stacks/appconfig/: make deploy, make destroy
# Or from infra/: make deploy-appconfig (orchestrator delegates here)

# AWS SAM configuration
# WARNING: do not edit these files manually, they are managed by AWS SAM.
SAM_CONFIG                := ../../../samconfig.toml
TEMPLATE                  := template.yaml
CAPABILITIES              ?= CAPABILITY_IAM
S3_BUCKET                 ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

# Configurable AWS stack variables
STACK_NAME                ?= cloudshortener-appconfig-dev
APP_NAME                  ?= cloudshortener
APP_ENV                   ?= dev
AWS_REGION                ?= eu-central-1
AWS_PROFILE               ?= personal-dev

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: build deploy destroy pre-destroy delete-hosted-configuration-versions help

help:
	@echo "AppConfig stack, hosting cloudshortener's backend configuration"
	@echo ""
	@echo "Deploys AWS AppConfig: application, environment, configuration profile, and hosted"
	@echo "configuration version. Used by the backend to fetch runtime config (e.g. Redis"
	@echo "connection details). No dependencies."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make deploy                               - Deploy AppConfig stack"
	@echo "  make destroy                              - Destroy AppConfig stack"
	@echo "  make delete-hosted-configuration-versionss - Delete hosted config versions (run before destroy)"
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
	@echo "No build needed for appconfig stack"

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

delete-hosted-configuration-versions:
	@APP_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--query "Stacks[0].Outputs[?OutputKey=='AppConfigApplicationId'].OutputValue" \
		--output text 2>/dev/null); \
	PROFILE_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--query "Stacks[0].Outputs[?OutputKey=='BackendConfigProfileId'].OutputValue" \
		--output text 2>/dev/null); \
	if [ -n "$$APP_ID" ] && [ -n "$$PROFILE_ID" ]; then \
		HOSTED_CONFIGURATION_VERSIONS=$$(aws appconfig list-hosted-configuration-versions \
			--application-id $$APP_ID \
			--configuration-profile-id $$PROFILE_ID \
			--region $(AWS_REGION) \
			--profile $(AWS_PROFILE) \
			--query 'Items[*].VersionNumber' \
			--output text 2>/dev/null); \
		for ver in $$HOSTED_CONFIGURATION_VERSIONS; do \
			aws appconfig delete-hosted-configuration-version \
				--application-id $$APP_ID \
				--configuration-profile-id $$PROFILE_ID \
				--version-number $$ver \
				--region $(AWS_REGION) \
				--profile $(AWS_PROFILE) 2>/dev/null || true; \
		done; \
		echo "Hosted configuration versions deleted."; \
	fi

pre-destroy:
	$(MAKE) delete-hosted-configuration-versions

destroy:
	$(call confirm_destroy,$(STACK_NAME))
	$(MAKE) pre-destroy
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts
