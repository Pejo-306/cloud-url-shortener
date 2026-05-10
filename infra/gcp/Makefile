# --- Application ---
APP_NAME                      ?= cloudshortener
APP_ENV                       ?= dev
PROJECT_ID                    ?= $(APP_NAME)-$(APP_ENV)

# --- Terraform backend ---
STATE_BUCKET                  ?=
PROJECT_STATE_PREFIX  := env/$(APP_ENV)/project
WORKLOAD_STATE_PREFIX := env/$(APP_ENV)/workload

# --- Cloud Function artifacts ---
ARTIFACTS_BUCKET              ?=
CLOUD_FUNCTIONS_SOURCE_DIR    ?= admin/placeholders/functions
CLOUD_FUNCTIONS_ARTIFACTS_DIR ?= .artifacts/cloud-functions

# --- GCP project configuration ---
REGION                        ?= europe-west1
BILLING_ACCOUNT               ?=
ORG_ID                        ?=
FOLDER_ID                     ?=
BROWSER_API_KEY_GENERATION    ?= v1

# --- Workload configuration ---
LOG_LEVEL                     ?= INFO
SUBNET_CIDR                   ?= 10.0.1.0/24
MEMORYSTORE_MEMORY_SIZE_GB    ?= 1
FRONTEND_DOMAIN               ?=

# --- Redis Cloud (primary datastore) ---
REDIS_CLOUD_HOST              ?=
REDIS_CLOUD_PORT              ?= 6379
REDIS_CLOUD_DB                ?= 0
REDIS_CLOUD_USER              ?=
REDIS_CLOUD_PASS              ?=

# --- Generated tfvars (internal) ---
MAKE_DIR                      := .make
PROJECTS_VAR_FILE             := $(MAKE_DIR)/$(APP_ENV).projects.tfvars
WORKLOAD_VAR_FILE             := $(MAKE_DIR)/$(APP_ENV).workload.tfvars
WORKLOAD_PLAN_FILE            := $(MAKE_DIR)/$(APP_ENV).tfplan

# --- Terraform execution ---
TF_USE_PLAN_FILE              ?=
TF_EXTRA_ARGS                 ?=
TF_AUTO_APPROVE               ?=
PROJECT_INIT_ARGS             := -reconfigure -backend-config="bucket=$(STATE_BUCKET)" -backend-config="prefix=$(PROJECT_STATE_PREFIX)"
WORKLOAD_INIT_ARGS            := -reconfigure -backend-config="bucket=$(STATE_BUCKET)" -backend-config="prefix=$(WORKLOAD_STATE_PREFIX)"
APPLY_EXTRA_ARGS              := $(TF_EXTRA_ARGS)
ifeq ($(TF_AUTO_APPROVE),true)
APPLY_EXTRA_ARGS              += -auto-approve
endif

YELLOW      := \033[33m
RED         := \033[31m
BOLD_YELLOW := \033[1;33m
BOLD_RED    := \033[1;31m
RESET       := \033[0m


.PHONY: help init build deploy-project deploy destroy

help:
	@echo "CloudShortener GCP environment orchestrator."
	@echo ""
	@echo "E2E deploy and teardown of one environment-scoped GCP project & workload."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make help                                 - Show this message"
	@echo "  make init                                 - Initialize projects and workload Terraform roots"
	@echo "  make build                                - Build function zips and the workload Terraform plan"
	@echo "  make deploy-project                       - Create GCP project and enable service APIs"
	@echo "  make deploy                               - Create the full environment stack"
	@echo "  make destroy                              - Destroy workload, then project-level resources"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  APP_ENV                                   - Environment name (default: dev)"
	@echo "  APP_NAME                                  - Application name (default: cloudshortener)"
	@echo "  PROJECT_ID                                - GCP env project id (default: $(APP_NAME)-$(APP_ENV))"
	@echo "  REGION                                    - GCP region (default: europe-west1)"
	@echo "  BILLING_ACCOUNT                           - Billing account id (required for deploy)"
	@echo "  ORG_ID                                    - Organization id for project creation"
	@echo "  FOLDER_ID                                 - Folder id for project creation"
	@echo "  STATE_BUCKET                              - Terraform state bucket (required)"
	@echo "  ARTIFACTS_BUCKET                          - Function artifacts bucket (required for deploy)"
	@echo "  REDIS_CLOUD_USER                          - Redis Cloud username (required for deploy)"
	@echo "  REDIS_CLOUD_PASS                          - Redis Cloud password (required for deploy)"
	@echo "  TF_USE_PLAN_FILE                          - Set to \"true\" to apply the saved workload plan"
	@echo "  WORKLOAD_PLAN_FILE                        - Saved workload plan path (default: $(WORKLOAD_PLAN_FILE))"
	@echo "  TF_EXTRA_ARGS                             - Extra flags appended to Terraform apply/plan commands"
	@echo "  TF_AUTO_APPROVE                           - Set to \"true\" to append -auto-approve to apply/destroy"
	@echo ""
	@echo "\033[1mUsage:\033[0m"
	@echo "  make deploy \\"
	@echo "    APP_ENV=staging \\"
	@echo "    STATE_BUCKET=cloudshortener-tf-state-881520955141 \\"
	@echo "    ARTIFACTS_BUCKET=cloudshortener-artifacts-881520955141 \\"
	@echo "    BILLING_ACCOUNT=012345-ABCDEF-678901 \\"
	@echo "    ORG_ID=123456789 \\"
	@echo "    REDIS_CLOUD_USER=default \\"
	@echo "    REDIS_CLOUD_PASS=your-redis-password \\"
	@echo "    TF_AUTO_APPROVE=true"
	@echo ""
	@echo "  make destroy \\"
	@echo "    APP_ENV=staging \\"
	@echo "    STATE_BUCKET=cloudshortener-tf-state-881520955141 \\"
	@echo "    TF_AUTO_APPROVE=true"

init: _require_state_bucket
	$(MAKE) -C projects init TF_EXTRA_ARGS='$(PROJECT_INIT_ARGS)'
	$(MAKE) -C workload init TF_EXTRA_ARGS='$(WORKLOAD_INIT_ARGS)'

build: _require_deployed_project
	$(MAKE) _build_function_zips
	@$(MAKE) _generate_workload_tfvars
	$(MAKE) -C workload build \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(WORKLOAD_VAR_FILE) \
		TF_PLAN_FILE=../$(WORKLOAD_PLAN_FILE) \
		TF_EXTRA_ARGS='$(TF_EXTRA_ARGS)'

deploy-project: _deploy_requirements
	@$(MAKE) _generate_projects_tfvars
	$(MAKE) _import_project_if_exists
	$(MAKE) _create_project
	$(MAKE) _enable_bootstrap_apis
	$(MAKE) _poll_cloud_billing
	$(MAKE) _enable_service_apis

	$(MAKE) _import_identity_platform_if_exists
	$(MAKE) _deploy_project_resources
	$(MAKE) _configure_identity_platform_password_policy
	$(MAKE) _seed_redis_cloud_secret
	$(MAKE) _poll_iam_bindings

# Step 1: Create GCP project and enable service APIs
# Step 2: Deploy project resources
# Step 3: Build and deploy workload resources
deploy: init
	$(MAKE) deploy-project
	$(MAKE) build
	$(MAKE) _upload_function_zips
	$(MAKE) _deploy_workload_resources TF_USE_PLAN_FILE=true

destroy: init
	$(MAKE) _destroy_workload
	$(MAKE) _destroy_project

# --- Private make targets ---

.PHONY: _deploy_requirements
_deploy_requirements: _require_state_bucket _require_artifacts_bucket _require_billing_account _require_org_id_or_folder_id _require_redis_cloud_user_and_pass

.PHONY: _require_state_bucket
_require_state_bucket:
	@if [ -z "$(STATE_BUCKET)" ]; then \
		echo "$(BOLD_RED)| ERROR: STATE_BUCKET is required for init$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_artifacts_bucket
_require_artifacts_bucket:
	@if [ -z "$(ARTIFACTS_BUCKET)" ]; then \
		echo "$(BOLD_RED)| ERROR: ARTIFACTS_BUCKET is required for deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_billing_account
_require_billing_account:
	@if [ -z "$(BILLING_ACCOUNT)" ]; then \
		echo "$(BOLD_RED)| ERROR: BILLING_ACCOUNT is required for deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_org_id_or_folder_id
_require_org_id_or_folder_id:
	@if [ -z "$(ORG_ID)" ] && [ -z "$(FOLDER_ID)" ]; then \
		echo "$(BOLD_RED)| ERROR: ORG_ID or FOLDER_ID is required for deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_redis_cloud_user_and_pass
_require_redis_cloud_user_and_pass:
	@if [ -z "$(REDIS_CLOUD_USER)" ] || [ -z "$(REDIS_CLOUD_PASS)" ]; then \
		echo "$(BOLD_RED)| ERROR: REDIS_CLOUD_USER and REDIS_CLOUD_PASS are required for deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_deployed_project
_require_deployed_project:
	@project_number="$$(terraform -chdir=projects output -raw project_number 2>/dev/null || true)"; \
	is_valid_project_number="printf '%s' \"\$$project_number\" | grep -Eq '^[0-9]+\$$'"; \
	if ! eval "$$is_valid_project_number"; then \
		echo "$(BOLD_RED)| ERROR: Cannot build workload plan before the projects stack is deployed$(RESET)"; \
		echo "$(RED)| Run \`make deploy-project\` first for a new environment.$(RESET)"; \
		exit 1; \
	fi

.PHONY: _create_project
_create_project:
	$(MAKE) -C projects deploy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(PROJECTS_VAR_FILE) \
		TF_USE_PLAN_FILE= \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS) -target="google_project.this[0]"'

.PHONY: _import_project_if_exists
_import_project_if_exists:
	./scripts/import-project-if-exists.sh projects ../$(PROJECTS_VAR_FILE) $(PROJECT_ID)

.PHONY: _enable_service_apis
_enable_service_apis:
	$(MAKE) -C projects deploy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(PROJECTS_VAR_FILE) \
		TF_USE_PLAN_FILE= \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS) -target="google_project_service.apis"'

.PHONY: _import_identity_platform_if_exists
_import_identity_platform_if_exists:
	./scripts/import-identity-platform-if-exists.sh projects ../$(PROJECTS_VAR_FILE)

.PHONY: _deploy_project_resources
_deploy_project_resources:
	$(MAKE) -C projects deploy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(PROJECTS_VAR_FILE) \
		TF_USE_PLAN_FILE= \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS)'

.PHONY: _set_project_abandon_policy
_set_project_abandon_policy:
	$(MAKE) -C projects deploy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(PROJECTS_VAR_FILE) \
		TF_USE_PLAN_FILE= \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS) -var deletion_policy=ABANDON -target="google_project.this[0]"'

.PHONY: _destroy_workload
_destroy_workload:
	@if ! terraform -chdir=workload state list 2>/dev/null | grep -q .; then \
		echo "destroy-workload: state is empty, skipping"; \
	else \
		$(MAKE) _generate_workload_tfvars && \
		$(MAKE) -C workload destroy \
			APP_ENV=$(APP_ENV) \
			TF_VAR_FILE=../$(WORKLOAD_VAR_FILE) \
			TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS)'; \
	fi

.PHONY: _destroy_project
_destroy_project:
	@$(MAKE) _generate_projects_tfvars
	@if terraform -chdir=projects state list 2>/dev/null | grep -q 'google_project\.this'; then \
		$(MAKE) _set_project_abandon_policy; \
	fi
	$(MAKE) -C projects destroy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(PROJECTS_VAR_FILE) \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS)'

.PHONY: _deploy_workload_resources
_deploy_workload_resources:
	$(MAKE) -C workload deploy \
		APP_ENV=$(APP_ENV) \
		TF_VAR_FILE=../$(WORKLOAD_VAR_FILE) \
		TF_PLAN_FILE=../$(WORKLOAD_PLAN_FILE) \
		TF_USE_PLAN_FILE=$(TF_USE_PLAN_FILE) \
		TF_EXTRA_ARGS='$(APPLY_EXTRA_ARGS)'

.PHONY: _build_function_zips
_build_function_zips:
	./scripts/build-function-zips.sh "$(CLOUD_FUNCTIONS_SOURCE_DIR)" "$(CLOUD_FUNCTIONS_ARTIFACTS_DIR)"

.PHONY: _enable_bootstrap_apis
_enable_bootstrap_apis:
	./scripts/enable-bootstrap-apis.sh $(PROJECT_ID)

.PHONY: _poll_cloud_billing
_poll_cloud_billing:
	./scripts/poll-cloud-billing.sh $(PROJECT_ID)

.PHONY: _configure_identity_platform_password_policy
_configure_identity_platform_password_policy:
	./scripts/configure-identity-platform-password-policy.sh $(PROJECT_ID)

.PHONY: _seed_redis_cloud_secret
_seed_redis_cloud_secret:
	@./scripts/seed-redis-cloud-secret.sh \
		$(PROJECT_ID) \
		$(APP_NAME) \
		$(APP_ENV) \
		"$(REDIS_CLOUD_USER)" \
		"$(REDIS_CLOUD_PASS)"

.PHONY: _upload_function_zips
_upload_function_zips:
	./scripts/upload-function-zips.sh "$(CLOUD_FUNCTIONS_ARTIFACTS_DIR)" "$(ARTIFACTS_BUCKET)" "$(APP_ENV)"

.PHONY: _poll_iam_bindings
_poll_iam_bindings:
	./scripts/poll-iam-bindings.sh $(PROJECT_ID) $(APP_ENV)

.PHONY: _generate_projects_tfvars
_generate_projects_tfvars:
	@mkdir -p $(MAKE_DIR)
	@env \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		PROJECT_ID="$(PROJECT_ID)" \
		REGION="$(REGION)" \
		BILLING_ACCOUNT="$(BILLING_ACCOUNT)" \
		ORG_ID="$(ORG_ID)" \
		FOLDER_ID="$(FOLDER_ID)" \
		BROWSER_API_KEY_GENERATION="$(BROWSER_API_KEY_GENERATION)" \
		./scripts/generate-projects-tfvars.sh "$(PROJECTS_VAR_FILE)"

.PHONY: _generate_workload_tfvars
_generate_workload_tfvars:
	@mkdir -p $(MAKE_DIR)
	@env \
		APP_NAME="$(APP_NAME)" \
		APP_ENV="$(APP_ENV)" \
		PROJECT_ID="$(PROJECT_ID)" \
		REGION="$(REGION)" \
		LOG_LEVEL="$(LOG_LEVEL)" \
		SUBNET_CIDR="$(SUBNET_CIDR)" \
		MEMORYSTORE_MEMORY_SIZE_GB="$(MEMORYSTORE_MEMORY_SIZE_GB)" \
		REDIS_CLOUD_HOST="$(REDIS_CLOUD_HOST)" \
		REDIS_CLOUD_PORT="$(REDIS_CLOUD_PORT)" \
		REDIS_CLOUD_DB="$(REDIS_CLOUD_DB)" \
		FRONTEND_DOMAIN="$(FRONTEND_DOMAIN)" \
		ARTIFACTS_BUCKET="$(ARTIFACTS_BUCKET)" \
		./scripts/generate-workload-tfvars.sh projects "$(WORKLOAD_VAR_FILE)"
