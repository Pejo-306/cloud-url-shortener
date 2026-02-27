# infra/bootstrap/Makefile
# Run from infra/bootstrap/: make oidc-up, make seed-ssm, etc.
# Or from infra/: make -C bootstrap <target>
#
# Bootstrap stack: GitHub OIDC, deploy role, CloudFormation exec role.
# Seeding scripts: SSM params, Secrets Manager, ElastiCache creds/params.

# Configurable variables (override via: make oidc-up GITHUB_ORG=my-org)
STACK_NAME     ?= cloudshortener-bootstrap
APP_NAME       ?= cloudshortener
APP_ENV        ?= dev
GITHUB_ORG     ?= Pejo-306
REPO_NAME      ?= cloud-url-shortener
AWS_REGION     ?= eu-central-1
AWS_PROFILE    ?= personal-dev
CONFIG_ROOT    ?= ../../config

# ElastiCache defaults (override for seed-elasticache-* targets)
ELASTICACHE_USER     ?= default
ELASTICACHE_PORT     ?= 6379
ELASTICACHE_DB       ?= 0

define confirm_destroy
	@read -p "Destroy stack $(1)? [y/N]: " ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ] || (echo "Aborted." && exit 1)
endef

.PHONY: oidc-up oidc-down seed-ssm seed-secrets seed-elasticache-secrets seed-elasticache-ssm help

help:
	@echo "Bootstrap stack and seeding scripts for cloudshortener"
	@echo ""
	@echo "OIDC stack: GitHub OIDC provider, deploy role, CloudFormation exec role."
	@echo "Seeding: SSM params, Secrets Manager, ElastiCache creds from config YAMLs."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make oidc-up                      - Deploy OIDC bootstrap stack"
	@echo "  make oidc-down                    - Delete OIDC bootstrap stack"
	@echo "  make seed-ssm                     - Seed SSM parameters from config/"
	@echo "  make seed-secrets                 - Seed Secrets Manager from config/"
	@echo "  make seed-elasticache-secrets     - Seed ElastiCache password (pre-deploy)"
	@echo "  make seed-elasticache-ssm         - Seed ElastiCache SSM params (post-deploy)"
	@echo "  make help                         - Show this message"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make oidc-up GITHUB_ORG=my-org)"
	@echo "  STACK_NAME                       - CloudFormation stack name"
	@echo "  APP_NAME                         - Application name"
	@echo "  APP_ENV                          - Environment (dev, staging, prod)"
	@echo "  GITHUB_ORG                       - GitHub org/username for OIDC"
	@echo "  REPO_NAME                        - GitHub repo name"
	@echo "  AWS_REGION                       - AWS region"
	@echo "  AWS_PROFILE                      - AWS profile"
	@echo "  CONFIG_ROOT                      - Config directory (default: ../../config)"
	@echo ""
	@echo "\033[1mTarget-specific variables:\033[0m"
	@echo "  oidc-up:"
	@echo "    EXISTING_OIDC_PROVIDER_ARN     - Use existing OIDC provider ARN (no default)"
	@echo ""
	@echo "  seed-elasticache-secrets:"
	@echo "    ELASTICACHE_PASSWORD, PASSWORD - Password (required)"
	@echo "    ELASTICACHE_USER               - Redis user (default: default)"
	@echo ""
	@echo "  seed-elasticache-ssm:"
	@echo "    ELASTICACHE_HOST, HOST         - Redis host (required)"
	@echo "    ELASTICACHE_PORT               - Redis port (default: 6379)"
	@echo "    ELASTICACHE_DB                 - Redis DB index (default: 0)"
	@echo "    ELASTICACHE_USER               - Redis user (default: default)"
	@echo ""
	@echo "\033[1mPass extra script args:\033[0m use ARGS=\"...\" for any target"
	@echo "  make seed-ssm ARGS=\"--dry-run --tags Owner=Pesho\""
	@echo "  make oidc-up ARGS=\"--dry-run --no-watch\""
	@echo "  make oidc-up EXISTING_OIDC_PROVIDER_ARN=arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
	@echo ""

# OIDC stack targets
# EXISTING_OIDC_PROVIDER_ARN: optional, no default. When set, passed as --parameter-overrides ExistingOidcProviderArn=...
oidc-up: DEFAULT_ARGS :=
oidc-up:
	uv run python -m scripts.bootstrap_oidc up \
		--stack-name $(STACK_NAME) \
		--github-org $(GITHUB_ORG) \
		--repo $(REPO_NAME) \
		--aws-profile $(AWS_PROFILE) \
		$(if $(EXISTING_OIDC_PROVIDER_ARN),--parameter-overrides "ExistingOidcProviderArn=$(EXISTING_OIDC_PROVIDER_ARN)") \
		$(or $(ARGS),$(DEFAULT_ARGS))

oidc-down: DEFAULT_ARGS :=
oidc-down:
	$(call confirm_destroy,$(STACK_NAME))
	uv run python -m scripts.bootstrap_oidc down \
		--stack-name $(STACK_NAME) \
		--aws-profile $(AWS_PROFILE) \
		$(or $(ARGS),$(DEFAULT_ARGS))

# Seeding targets
seed-ssm: DEFAULT_ARGS :=
seed-ssm:
	uv run python -m scripts.seed_ssm_params \
		--app-name $(APP_NAME) \
		--root $(CONFIG_ROOT) \
		--env-allow $(APP_ENV) \
		--aws-profile $(AWS_PROFILE) \
		$(or $(ARGS),$(DEFAULT_ARGS))

seed-secrets: DEFAULT_ARGS :=
seed-secrets:
	uv run python -m scripts.seed_secrets \
		--app-name $(APP_NAME) \
		--root $(CONFIG_ROOT) \
		--env-allow $(APP_ENV) \
		--aws-profile $(AWS_PROFILE) \
		$(or $(ARGS),$(DEFAULT_ARGS))

seed-elasticache-secrets: DEFAULT_ARGS :=
seed-elasticache-secrets:
ifeq ($(or $(ELASTICACHE_PASSWORD),$(PASSWORD)),)
	$(error ELASTICACHE_PASSWORD or PASSWORD is required. Example: make seed-elasticache-secrets ELASTICACHE_PASSWORD='your-password')
endif
	uv run python -m scripts.seed_elasticache \
		--secrets-only \
		--app-name $(APP_NAME) \
		--env $(APP_ENV) \
		--user $(ELASTICACHE_USER) \
		--password $(or $(ELASTICACHE_PASSWORD),$(PASSWORD)) \
		--aws-profile $(AWS_PROFILE) \
		$(or $(ARGS),$(DEFAULT_ARGS))

seed-elasticache-ssm: DEFAULT_ARGS :=
seed-elasticache-ssm:
ifeq ($(or $(ELASTICACHE_HOST),$(HOST)),)
	$(error ELASTICACHE_HOST or HOST is required. Example: make seed-elasticache-ssm ELASTICACHE_HOST=redis.example.com)
endif
	uv run python -m scripts.seed_elasticache \
		--ssm-only \
		--app-name $(APP_NAME) \
		--env $(APP_ENV) \
		--host $(or $(ELASTICACHE_HOST),$(HOST)) \
		--port $(ELASTICACHE_PORT) \
		--db $(ELASTICACHE_DB) \
		--user $(ELASTICACHE_USER) \
		--aws-profile $(AWS_PROFILE) \
		$(or $(ARGS),$(DEFAULT_ARGS))
