# infra/stacks/backend/Makefile
# Run from infra/stacks/backend/: make build, make deploy, make destroy
# Or from infra/: make deploy-backend (orchestrator delegates here)

# AWS SAM configuration
# WARNING: do not edit these files manually, they are managed by AWS SAM.
SAM_CONFIG                := ../../../samconfig.toml
TEMPLATE                  := template.yaml
CAPABILITIES              ?= CAPABILITY_IAM
S3_BUCKET                 ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

# Configurable AWS stack variables
STACK_NAME                ?= cloudshortener-backend-dev
APP_NAME                  ?= cloudshortener
APP_ENV                   ?= dev
LOG_LEVEL                 ?= INFO
AWS_REGION                ?= eu-central-1
AWS_PROFILE               ?= personal-dev

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

# Dependencies (from Network, Cognito, AppConfig stacks - required for deploy)
## Network stack dependencies
PRIVATE_SUBNET_A           ?=
PRIVATE_SUBNET_B           ?=
LAMBDA_SECURITY_GROUP_ID   ?=
## Cognito stack dependencies
USER_POOL_ID               ?=
USER_POOL_ARN              ?=
USER_POOL_CLIENT_ID        ?=
## AppConfig stack dependencies
APPCONFIG_APPLICATION_ID   ?=
APPCONFIG_ENVIRONMENT_ID   ?=
BACKEND_CONFIG_PROFILE_ID  ?=

.PHONY: build deploy deploy-standalone destroy help

help:
	@echo "Backend stack"
	@echo ""
	@echo "Deploys API Gateway, Lambda functions, and IAM role. Builds Python code with"
	@echo "sam build --use-container."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make build                                - Build Lambda with sam build --use-container"
	@echo "  make deploy                               - Build and deploy (requires deps from Network, Cognito, AppConfig)"
	@echo "  make deploy-standalone                    - Build and deploy without VPC/Cognito/AppConfig (local-dev style)"
	@echo "  make destroy                              - Destroy backend stack"
	@echo "  make help                                 - Show this message"
	@echo ""
	@echo "\033[1mDependencies:\033[0m (required for deploy, from other stack outputs)"
	@echo "  PRIVATE_SUBNET_A                          - Private Subnet A ID (Network)"
	@echo "  PRIVATE_SUBNET_B                          - Private Subnet B ID (Network)"
	@echo "  LAMBDA_SECURITY_GROUP_ID                  - Lambda Security Group ID (Network)"
	@echo "  USER_POOL_ID                              - Cognito User Pool ID"
	@echo "  USER_POOL_ARN                             - Cognito User Pool ARN"
	@echo "  USER_POOL_CLIENT_ID                       - Cognito User Pool Client ID"
	@echo "  APPCONFIG_APPLICATION_ID                  - AppConfig Application ID"
	@echo "  APPCONFIG_ENVIRONMENT_ID                  - AppConfig Environment ID"
	@echo "  BACKEND_CONFIG_PROFILE_ID                 - AppConfig Backend Config Profile ID"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  STACK_NAME                                - CloudFormation stack name"
	@echo "  APP_NAME                                  - Application name"
	@echo "  APP_ENV                                   - Environment (dev, staging, prod)"
	@echo "  LOG_LEVEL                                 - Logging level (DEBUG, INFO, etc.)"
	@echo "  S3_BUCKET                                 - S3 bucket for SAM artifacts"
	@echo "  AWS_REGION                                - AWS region"
	@echo "  AWS_PROFILE                               - AWS profile"
	@echo ""
	@echo "\033[1mExamples:\033[0m"
	@echo "  make deploy PRIVATE_SUBNET_A=subnet-xxx PRIVATE_SUBNET_B=subnet-yyy ..."
	@echo "  make deploy-standalone"
	@echo ""

build:
	sam build \
		-t $(TEMPLATE) \
		--use-container

deploy: build
	@if [ -z "$(PRIVATE_SUBNET_A)" ] || [ -z "$(PRIVATE_SUBNET_B)" ] || [ -z "$(LAMBDA_SECURITY_GROUP_ID)" ] || \
		[ -z "$(USER_POOL_ID)" ] || [ -z "$(USER_POOL_ARN)" ] || [ -z "$(USER_POOL_CLIENT_ID)" ] || \
		[ -z "$(APPCONFIG_APPLICATION_ID)" ] || [ -z "$(APPCONFIG_ENVIRONMENT_ID)" ] || [ -z "$(BACKEND_CONFIG_PROFILE_ID)" ]; then \
		echo "ERROR: Backend deploy requires parameters from Network, Cognito, and AppConfig stacks."; \
		echo ""; \
		echo "Required:"; \
		echo "  (from Network stack)  	PRIVATE_SUBNET_A, PRIVATE_SUBNET_B, LAMBDA_SECURITY_GROUP_ID"; \
		echo "  (from Cognito stack)  	USER_POOL_ID, USER_POOL_ARN, USER_POOL_CLIENT_ID"; \
		echo "  (from AppConfig stack)  APPCONFIG_APPLICATION_ID, APPCONFIG_ENVIRONMENT_ID, BACKEND_CONFIG_PROFILE_ID"; \
		echo ""; \
		echo "Example:"; \
		echo "  make deploy \\"; \
		echo "    PRIVATE_SUBNET_A=subnet-xxx \\"; \
		echo "    PRIVATE_SUBNET_B=subnet-yyy \\"; \
		echo "    LAMBDA_SECURITY_GROUP_ID=sg-xxx \\"; \
		echo "    USER_POOL_ID=eu-central-1_xxx \\"; \
		echo "    USER_POOL_ARN=arn:aws:cognito:... \\"; \
		echo "    USER_POOL_CLIENT_ID=xxx \\"; \
		echo "    APPCONFIG_APPLICATION_ID=xxx \\"; \
		echo "    APPCONFIG_ENVIRONMENT_ID=xxx \\"; \
		echo "    BACKEND_CONFIG_PROFILE_ID=xxx"; \
		echo ""; \
		echo "Or use: make deploy-standalone  (deploys without VPC/Cognito/AppConfig)"; \
		exit 1; \
	fi
	sam deploy \
		--config-file $(SAM_CONFIG) \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--capabilities $(CAPABILITIES) \
		--s3-bucket $(S3_BUCKET) \
		--parameter-overrides \
			AppEnv=$(APP_ENV) \
			AppName=$(APP_NAME) \
			LogLevel=$(LOG_LEVEL) \
			PrivateSubnetA=$(PRIVATE_SUBNET_A) \
			PrivateSubnetB=$(PRIVATE_SUBNET_B) \
			LambdaSecurityGroupId=$(LAMBDA_SECURITY_GROUP_ID) \
			UserPoolId=$(USER_POOL_ID) \
			UserPoolArn=$(USER_POOL_ARN) \
			UserPoolClientId=$(USER_POOL_CLIENT_ID) \
			AppConfigApplicationId=$(APPCONFIG_APPLICATION_ID) \
			AppConfigEnvironmentId=$(APPCONFIG_ENVIRONMENT_ID) \
			BackendConfigProfileId=$(BACKEND_CONFIG_PROFILE_ID)

deploy-standalone: build
	sam deploy \
		--config-file $(SAM_CONFIG) \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--capabilities $(CAPABILITIES) \
		--s3-bucket $(S3_BUCKET) \
		--parameter-overrides \
			AppEnv=$(APP_ENV) \
			AppName=$(APP_NAME) \
			LogLevel=$(LOG_LEVEL)

destroy:
	$(call confirm_destroy,$(STACK_NAME))
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts
