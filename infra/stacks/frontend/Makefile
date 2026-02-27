# infra/stacks/frontend/Makefile
# Run from infra/stacks/frontend/: make deploy, make destroy
# Or from infra/: make deploy-frontend (orchestrator delegates here)

# AWS SAM configuration
# WARNING: do not edit these files manually, they are managed by AWS SAM.
SAM_CONFIG                := ../../../samconfig.toml
TEMPLATE                  := template.yaml
CAPABILITIES              ?= CAPABILITY_IAM
S3_BUCKET                 ?= aws-sam-cli-managed-default-samclisourcebucket-4nqd7tupxtzl

# Configurable AWS stack variables
STACK_NAME                ?= cloudshortener-frontend-dev
APP_NAME                  ?= cloudshortener
APP_ENV                   ?= dev
FRONTEND_BUCKET_NAME      ?= cloudshortener-frontend
AWS_REGION                ?= eu-central-1
AWS_PROFILE               ?= personal-dev

# Path to frontend build output (relative to infra/stacks/frontend/)
FRONTEND_DIR              := ../../../frontend
FRONTEND_DIST             := $(FRONTEND_DIR)/dist

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: build deploy destroy pre-destroy sync empty-frontend-bucket help

help:
	@echo "Frontend cloudshortener stack - S3 hosting and CloudFront distribution"
	@echo ""
	@echo "Deploys S3 bucket for static hosting and CloudFront distribution with HTTPS."
	@echo "Optional: FRONTEND_BUCKET_NAME (default: cloudshortener-frontend). No dependencies."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make deploy                               - Deploy frontend stack"
	@echo "  make sync                                 - Sync frontend/dist/ to S3 and invalidate CloudFront"
	@echo "  make empty-frontend-bucket                - Empty S3 frontend bucket (run before destroy)"
	@echo "  make destroy                              - Destroy frontend stack"
	@echo "  make help                                 - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  STACK_NAME                                - CloudFormation stack name"
	@echo "  APP_NAME                                  - Application name"
	@echo "  APP_ENV                                   - Environment (dev, staging, prod)"
	@echo "  FRONTEND_BUCKET_NAME                      - S3 bucket name prefix"
	@echo "  AWS_REGION                                - AWS region"
	@echo "  AWS_PROFILE                               - AWS profile"
	@echo ""

build:
	$(MAKE) -C $(FRONTEND_DIR) build

sync:
	# Ensure frontend is compiled first
	@if [ ! -d "$(FRONTEND_DIST)" ]; then \
		echo ""; \
		echo "\033[1;33mWARNING: frontend/dist/ does not exist.\033[0m"; \
		echo ""; \
		echo "Build the frontend first:"; \
		echo "  cd frontend/"; \
		echo "  make build"; \
		echo ""; \
		echo "Then rerun from infra/stacks/frontend/:"; \
		echo "  make sync"; \
		echo ""; \
		exit 1; \
	fi

	# Check if stack is deployed to AWS
	@BUCKET=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
		--output text 2>/dev/null); \
	DIST_ID=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--query "Stacks[0].Outputs[?OutputKey=='CloudFrontDistributionId'].OutputValue" \
		--output text 2>/dev/null); \
	if [ -z "$$BUCKET" ] || [ -z "$$DIST_ID" ]; then \
		echo "ERROR: Could not get FrontendBucketName or CloudFrontDistributionId from stack $(STACK_NAME)."; \
		echo "Deploy the frontend stack first: make deploy"; \
		exit 1; \
	fi; \
	echo "Syncing $(FRONTEND_DIST)/ to s3://$$BUCKET/"; \
	aws s3 sync $(FRONTEND_DIST)/ s3://$$BUCKET/ \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--delete; \
	echo "Invalidating CloudFront distribution $$DIST_ID"; \
	aws cloudfront create-invalidation \
		--distribution-id $$DIST_ID \
		--paths "$$(echo '/*')" \
		--profile $(AWS_PROFILE) \
		--output text --query 'Invalidation.Id'; \
	echo "Sync complete. CloudFront invalidation in progress."

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
			AppName=$(APP_NAME) \
			FrontendBucketName=$(FRONTEND_BUCKET_NAME)

# Empty versioned S3 bucket:
# - delete all object versions
# - delete markers
# - abort incomplete multipart uploads
#
# Necessary because plain "aws s3 rm --recursive" only adds delete markers and leaves previous versions
# so CloudFormation cannot delete the bucket.
empty-frontend-bucket:
	@export AWS_PAGER=""; \
	BUCKET=$$(aws cloudformation describe-stacks \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
		--output text --no-cli-auto-prompt 2>/dev/null); \
	if [ -n "$$BUCKET" ]; then \
		echo "Emptying s3://$$BUCKET/ (all versions + multipart uploads)"; \
		export BUCKET AWS_REGION="$(AWS_REGION)" AWS_PROFILE="$(AWS_PROFILE)"; \
		while true; do \
			OUT=$$(aws s3api list-object-versions --bucket "$$BUCKET" \
				--region "$$AWS_REGION" --profile "$$AWS_PROFILE" --output json --no-cli-auto-prompt 2>/dev/null); \
			OBJS=$$(echo "$$OUT" | python3 -c "import sys,json; d=json.load(sys.stdin); v=d.get('Versions') or []; m=d.get('DeleteMarkers') or []; print(json.dumps({'Objects':[{'Key':x['Key'],'VersionId':x['VersionId']} for x in v+m if x.get('VersionId')]}))" 2>/dev/null); \
			CNT=$$(echo "$$OBJS" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('Objects',[])))" 2>/dev/null); \
			[ "$$CNT" = "0" ] && break; \
			aws s3api delete-objects --bucket "$$BUCKET" --delete "$$OBJS" \
				--region "$$AWS_REGION" --profile "$$AWS_PROFILE" --no-cli-auto-prompt 2>/dev/null || true; \
		done; \
		while true; do \
			MPU=$$(aws s3api list-multipart-uploads --bucket "$$BUCKET" \
				--region "$$AWS_REGION" --profile "$$AWS_PROFILE" --output json --no-cli-auto-prompt 2>/dev/null); \
			UP=$$(echo "$$MPU" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('Uploads') or []; print(u[0]['Key'] if u else '')" 2>/dev/null); \
			MPU_ID=$$(echo "$$MPU" | python3 -c "import sys,json; d=json.load(sys.stdin); u=d.get('Uploads') or []; print(u[0]['UploadId'] if u else '')" 2>/dev/null); \
			[ -z "$$MPU_ID" ] && break; \
			aws s3api abort-multipart-upload --bucket "$$BUCKET" --key "$$UP" --upload-id "$$MPU_ID" \
				--region "$$AWS_REGION" --profile "$$AWS_PROFILE" --no-cli-auto-prompt 2>/dev/null || true; \
		done; \
		echo "Frontend bucket emptied."; \
	fi

pre-destroy:
	$(MAKE) empty-frontend-bucket

destroy:
	$(call confirm_destroy,$(STACK_NAME))
	$(MAKE) pre-destroy
	sam delete \
		--stack-name $(STACK_NAME) \
		--region $(AWS_REGION) \
		--profile $(AWS_PROFILE) \
		--s3-bucket $(S3_BUCKET) \
		--no-prompts
