# infra/bastion/Makefile
# Run from infra/bastion/: make up, make connect, make down
#
# Creates an ephemeral SSM bastion host.
# Deploys into the `cloudshortener` VPC to port-forward to VPC resources (e.g. ElastiCache).

# AWS SAM configuration
SAM_CONFIG           := ../../samconfig.toml
TEMPLATE             := template.yaml
CAPABILITIES         ?= CAPABILITY_IAM
S3_BUCKET            ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl
SAM_DEPLOY_ARGS      ?=

# Configuration variables
APP_NAME             ?= cloudshortener
APP_ENV              ?= dev
STACK_NAME           ?= $(APP_NAME)-bastion-$(APP_ENV)
AWS_REGION           ?= eu-central-1
AWS_PROFILE          ?= personal-dev

# Orchestrator stack to resolve network outputs from
ORCHESTRATOR_STACK   ?= $(APP_NAME)-$(APP_ENV)

# Port-forwarding (for make connect)
LOCAL_PORT           ?= 16379
ELASTICACHE_PORT     ?= 6379

.PHONY: up down connect lint-template help

help:
	@echo "Bastion stack - Ephemeral SSM bastion host for integration testing"
	@echo ""
	@echo "Deploys an EC2 instance with SSM agent into a private subnet."
	@echo "Used to port-forward to VPC resources (e.g. ElastiCache). Typically used for integration tests."
	@echo "Requires a deployed cloudshortener orchestrator stack."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make up                                      - Deploy bastion host and wait for SSM readiness"
	@echo "  make down                                    - Destroy bastion host"
	@echo "  make connect                                 - Start SSM port-forward to ElastiCache Redis"
	@echo "  make lint-template                           - Validate and lint CloudFormation template"
	@echo "  make help                                    - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make up APP_ENV=staging)"
	@echo "  STACK_NAME                                   - CloudFormation stack name"
	@echo "  ORCHESTRATOR_STACK                           - Orchestrator stack name (to resolve network outputs)"
	@echo "  APP_NAME                                     - Application name"
	@echo "  APP_ENV                                      - Environment (dev, staging, prod)"
	@echo "  AWS_REGION                                   - AWS region"
	@echo "  AWS_PROFILE                                  - AWS credentials profile"
	@echo "  SAM_DEPLOY_ARGS                              - Extra args for sam deploy (default: --no-confirm-changeset)"
	@echo "  LOCAL_PORT                                   - Local port for port-forward (default: 16379)"
	@echo "  ELASTICACHE_PORT                             - Remote ElastiCache port (default: 6379)"
	@echo ""
	@echo "\033[1mUsage:\033[0m"
	@echo "  # Deploy bastion host (run once)"
	@echo "  make up"
	@echo ""
	@echo "  # Start SSM port-forwarding to VPC resources."
	@echo "  # Keeps the session open, use other terminals to connect."
	@echo "  make connect"
	@echo ""
	@echo "  # Tear down bastion host when done"
	@echo "  make down"
	@echo ""

lint-template:
	@echo "sam validate --lint --region $(AWS_REGION) -t $(TEMPLATE)"
	@sam validate --lint --region $(AWS_REGION) -t $(TEMPLATE)

# TODO: this should be decoupled from the orchestrator stack, i.e. require VPC ID,
# security group ID and subnet IDs as parameters. But we should also support retrieving
# the parameters from the orchestrator stack.
up:
	@NETWORK_STACK=$$(aws cloudformation describe-stack-resource \
		--stack-name $(ORCHESTRATOR_STACK) \
		--logical-resource-id NetworkStack \
		--query 'StackResourceDetail.PhysicalResourceId' \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) 2>/dev/null) || true; \
	if [ -z "$$NETWORK_STACK" ]; then \
		echo "ERROR: Could not resolve NetworkStack from orchestrator stack '$(ORCHESTRATOR_STACK)'."; \
		echo "Make sure the orchestrator stack is deployed: cd ../  &&  make deploy"; \
		exit 1; \
	fi; \
	SUBNET=$$(aws cloudformation describe-stacks \
		--stack-name "$$NETWORK_STACK" \
		--query "Stacks[0].Outputs[?OutputKey=='PrivateSubnetA'].OutputValue" \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)) && \
	SECURITY_GROUP=$$(aws cloudformation describe-stacks \
		--stack-name "$$NETWORK_STACK" \
		--query "Stacks[0].Outputs[?OutputKey=='LambdaSecurityGroupId'].OutputValue" \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)) && \
	echo "Network: subnet=$$SUBNET security_group=$$SECURITY_GROUP" && \
	sam deploy \
		--config-file $(SAM_CONFIG) \
		--template-file $(TEMPLATE) \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--capabilities $(CAPABILITIES) \
		--s3-bucket $(S3_BUCKET) \
		$(SAM_DEPLOY_ARGS) \
		--no-fail-on-empty-changeset \
		--parameter-overrides \
			AppName=$(APP_NAME) \
			AppEnv=$(APP_ENV) \
			SubnetId=$$SUBNET \
			SecurityGroupId=$$SECURITY_GROUP && \
	INSTANCE_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query "Stacks[0].Outputs[?OutputKey=='BastionInstanceId'].OutputValue" \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE)) && \
	echo "Bastion ready: $$INSTANCE_ID"

down:
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts

connect:
	@INSTANCE_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--query "Stacks[0].Outputs[?OutputKey=='BastionInstanceId'].OutputValue" \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) 2>/dev/null) || true; \
	ELASTICACHE_ENDPOINT=$$(aws cloudformation describe-stacks \
		--stack-name $(ORCHESTRATOR_STACK) \
		--query "Stacks[0].Outputs[?OutputKey=='ElastiCachePrimaryEndpoint'].OutputValue" \
		--output text \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) 2>/dev/null) || true; \
	if [ -z "$$INSTANCE_ID" ]; then \
		echo "ERROR: Bastion stack '$(STACK_NAME)' not found or has no BastionInstanceId output."; \
		echo "Run 'make up' first."; \
		exit 1; \
	fi; \
	if [ -z "$$ELASTICACHE_ENDPOINT" ]; then \
		echo "ERROR: Could not get ElastiCachePrimaryEndpoint from orchestrator stack '$(ORCHESTRATOR_STACK)'."; \
		exit 1; \
	fi; \
	REDIS_HOST=$$(echo "$$ELASTICACHE_ENDPOINT" | cut -d: -f1); \
	echo "Port-forwarding localhost:$(LOCAL_PORT) -> $$REDIS_HOST:$(ELASTICACHE_PORT) via bastion $$INSTANCE_ID"; \
	aws ssm start-session \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION) \
		--target "$$INSTANCE_ID" \
		--document-name AWS-StartPortForwardingSessionToRemoteHost \
		--parameters "{\"host\":[\"$$REDIS_HOST\"],\"portNumber\":[\"$(ELASTICACHE_PORT)\"],\"localPortNumber\":[\"$(LOCAL_PORT)\"]}"
