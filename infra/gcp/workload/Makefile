PROJECT_ID       ?=
APP_ENV          ?= dev
TF_VAR_FILE      ?= $(APP_ENV).terraform.tfvars
TF_PLAN_FILE     ?= $(APP_ENV).tfplan
TF_USE_PLAN_FILE ?=
TF_EXTRA_ARGS    ?=
FRONTEND_DIR     ?= ../../../frontend

YELLOW      := \033[33m
RED         := \033[31m
BOLD_YELLOW := \033[1;33m
BOLD_RED    := \033[1;31m
RESET       := \033[0m

.PHONY: help init build deploy destroy output sync validate format

help:
	@echo "CloudShortener workload infrastructure for one GCP environment."
	@echo ""
	@echo "Deploys the runtime pieces for APP_ENV=dev by default: networking, Memorystore,"
	@echo "backend services, frontend hosting, and runtime configuration."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make help                                 - Show this message"
	@echo "  make init                                 - Download providers and configure the backend"
	@echo "  make build                                - Create and save a Terraform plan"
	@echo "  make deploy                               - Apply changes, or the saved plan when TF_USE_PLAN_FILE=true"
	@echo "  make destroy                              - Tear down resources managed by this root"
	@echo "  make output                               - Print Terraform outputs"
	@echo "  make sync                                 - Sync frontend/dist/ to GCS and invalidate CDN"
	@echo "  make validate                             - Check formatting and validate Terraform configuration"
	@echo "  make format                               - Format Terraform files"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy APP_ENV=staging)"
	@echo "  PROJECT_ID                                - GCP project id"
	@echo "  APP_ENV                                   - Environment to operate on (default: dev)"
	@echo "  TF_VAR_FILE                               - Variables file to load (default: $(APP_ENV).terraform.tfvars)"
	@echo "  TF_PLAN_FILE                              - Saved plan file path (default: $(APP_ENV).tfplan)"
	@echo "  TF_USE_PLAN_FILE                          - Set to \"true\" to apply the saved plan"
	@echo "  TF_EXTRA_ARGS                             - Extra flags appended to every Terraform command"
	@echo "  FRONTEND_DIR                              - Frontend app directory"
	@echo ""
	@if [ ! -f "$(TF_VAR_FILE)" ]; then \
		echo "$(BOLD_YELLOW)| WARNING: Terraform variables file not found$(RESET)"; \
		echo "$(YELLOW)|$(RESET)"; \
		echo "$(YELLOW)| Terraform variables file: $(TF_VAR_FILE)$(RESET)"; \
		echo "$(YELLOW)|$(RESET)"; \
		echo "$(YELLOW)| Copy the example file and fill in your values:$(RESET)"; \
		echo "$(YELLOW)|   cp terraform.tfvars.example $(TF_VAR_FILE)$(RESET)"; \
		echo "$(YELLOW)|$(RESET)"; \
	fi

init:
	terraform init $(TF_EXTRA_ARGS)

build: _check_var_file
	terraform plan -out=$(TF_PLAN_FILE) -var-file=$(TF_VAR_FILE) $(TF_EXTRA_ARGS)

deploy: _check_var_file
ifeq ($(TF_USE_PLAN_FILE),true)
	terraform apply $(TF_PLAN_FILE)
else
	terraform apply -var-file=$(TF_VAR_FILE) $(TF_EXTRA_ARGS)
endif

destroy: _check_var_file
	terraform destroy -var-file=$(TF_VAR_FILE) $(TF_EXTRA_ARGS)

output:
	terraform output $(TF_EXTRA_ARGS)

sync: _sync_frontend

validate:
	terraform fmt -check -recursive $(TF_EXTRA_ARGS)
	terraform validate $(TF_EXTRA_ARGS)

format:
	terraform fmt -recursive $(TF_EXTRA_ARGS)

# --- Private make targets ---

.PHONY: _require_frontend_bucket
_require_frontend_bucket:
	@if [ -z "$$(terraform output -raw frontend_bucket_name 2>/dev/null)" ]; then \
		echo "$(BOLD_RED)| ERROR: Cannot read frontend_bucket_name from Terraform outputs.$(RESET)"; \
		echo "$(RED)| Deploy the workload stack first: make deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _require_frontend_url_map
_require_frontend_url_map:
	@if [ -z "$$(terraform output -raw frontend_url_map_name 2>/dev/null)" ]; then \
		echo "$(BOLD_RED)| ERROR: Cannot read frontend_url_map_name from Terraform outputs.$(RESET)"; \
		echo "$(RED)| Deploy the workload stack first: make deploy$(RESET)"; \
		exit 1; \
	fi

.PHONY: _check_var_file
_check_var_file:
	@if [ ! -f "$(TF_VAR_FILE)" ]; then \
		echo "$(BOLD_RED)| ERROR: Terraform variables file not found$(RESET)"; \
		echo "$(RED)|$(RESET)"; \
		echo "$(RED)| Terraform variables file: $(TF_VAR_FILE)$(RESET)"; \
		echo "$(RED)|$(RESET)"; \
		echo "$(RED)| Copy the example file and fill in your values:$(RESET)"; \
		echo "$(RED)|   cp terraform.tfvars.example $(TF_VAR_FILE)$(RESET)"; \
		echo "$(RED)|$(RESET)"; \
		exit 1; \
	fi

.PHONY: _sync_frontend
_sync_frontend: _require_frontend_bucket _require_frontend_url_map
	$(MAKE) -C $(FRONTEND_DIR) build MODE=$(APP_ENV)

	@BUCKET=$$(terraform output -raw frontend_bucket_name); \
	echo "Syncing $(FRONTEND_DIR)/dist/ -> gs://$$BUCKET/"; \
	gcloud storage rsync $(FRONTEND_DIR)/dist/ "gs://$$BUCKET/" --recursive --delete-unmatched-destination-objects

	@URL_MAP=$$(terraform output -raw frontend_url_map_name); \
	echo "Invalidating CDN cache on url-map $$URL_MAP"; \
	gcloud compute url-maps invalidate-cdn-cache "$$URL_MAP" --path "/*" --project "$(PROJECT_ID)"

	@echo "Frontend sync complete."
