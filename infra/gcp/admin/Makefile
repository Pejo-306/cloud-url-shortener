TF_VAR_FILE      ?= terraform.tfvars
TF_PLAN_FILE     ?= tfplan
TF_USE_PLAN_FILE ?=
TF_EXTRA_ARGS    ?=

YELLOW := \033[33m
RED    := \033[31m
BOLD_YELLOW := \033[1;33m
BOLD_RED    := \033[1;31m
RESET  := \033[0m

.PHONY: help init build deploy destroy output validate format
.PHONY: _check_var_file

help:
	@echo "Administrator project holding artifacts and Terraform state."
	@echo ""
	@echo "Provisions the admin GCP project + GCS buckets for Terraform remote state and deployment artifcats."
	@echo "Ensure this admin stack is up before attempting to provision any other project infrastructure."
	@echo ""
	@echo "\033[1mTargets:\033[0m"
	@echo "  make help                                 - Show this message"
	@echo "  make init                                 - Initialize Terraform (providers, backend)"
	@echo "  make build                                - Generate a Terraform plan (saved to TF_PLAN_FILE)"
	@echo "  make deploy                               - Apply infrastructure (plan file only if TF_USE_PLAN_FILE=true)"
	@echo "  make destroy                              - Destroy all managed resources"
	@echo "  make output                               - Show Terraform outputs"
	@echo "  make validate                             - Check formatting and validate configuration"
	@echo "  make format                               - Auto-format Terraform files"
	@echo ""
	@echo "\033[1mConfigurable variables:\033[0m (override via: make deploy TF_VAR_FILE=prod.tfvars)"
	@echo "  TF_VAR_FILE                               - Terraform variables file (default: terraform.tfvars)"
	@echo "  TF_PLAN_FILE                              - Plan file path for build/deploy (default: tfplan)"
	@echo "  TF_USE_PLAN_FILE                          - Must be \"true\" to deploy using the saved plan file"
	@echo "  TF_EXTRA_ARGS                             - Appended to every terraform command"
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
	terraform apply $(TF_PLAN_FILE) $(TF_EXTRA_ARGS)
else
	terraform apply -var-file=$(TF_VAR_FILE) $(TF_EXTRA_ARGS)
endif

destroy: _check_var_file
	terraform destroy -var-file=$(TF_VAR_FILE) $(TF_EXTRA_ARGS)

output:
	terraform output $(TF_EXTRA_ARGS)

validate:
	terraform fmt -check $(TF_EXTRA_ARGS)
	terraform validate $(TF_EXTRA_ARGS)

format:
	terraform fmt $(TF_EXTRA_ARGS)

# Private make targets follow.

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
