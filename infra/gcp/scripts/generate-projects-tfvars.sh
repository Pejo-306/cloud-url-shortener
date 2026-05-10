#!/usr/bin/env bash
# Generate project-stack Terraform variables from orchestrator Makefile inputs.
#
# Usage: generate-projects-tfvars.sh OUTPUT_FILE
# Env: APP_NAME, APP_ENV, PROJECT_ID, REGION, BILLING_ACCOUNT,
#      ORG_ID, FOLDER_ID, BROWSER_API_KEY_GENERATION

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 OUTPUT_FILE" >&2
  exit 1
fi

OUTPUT_FILE="$1"

hcl_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "${value}"
}

mkdir -p "$(dirname "${OUTPUT_FILE}")"

{
  printf 'app_name = %s\n' "$(hcl_string "${APP_NAME:-cloudshortener}")"
  printf 'app_env = %s\n' "$(hcl_string "${APP_ENV:-dev}")"
  printf 'region = %s\n' "$(hcl_string "${REGION:-europe-west1}")"
  printf 'project_id = %s\n' "$(hcl_string "${PROJECT_ID:?PROJECT_ID is required}")"
  printf 'create_project = true\n'

  if [[ -n "${BILLING_ACCOUNT:-}" ]]; then
    printf 'billing_account = %s\n' "$(hcl_string "${BILLING_ACCOUNT}")"
  fi

  if [[ -n "${ORG_ID:-}" ]]; then
    printf 'org_id = %s\n' "$(hcl_string "${ORG_ID}")"
  fi

  if [[ -n "${FOLDER_ID:-}" ]]; then
    printf 'folder_id = %s\n' "$(hcl_string "${FOLDER_ID}")"
  fi

  printf 'browser_api_key_generation = %s\n' "$(hcl_string "${BROWSER_API_KEY_GENERATION:-v1}")"
} >"${OUTPUT_FILE}"

echo "generate-projects-tfvars: wrote ${OUTPUT_FILE}"
