#!/usr/bin/env bash
# Generate workload-stack Terraform variables from orchestrator inputs and project outputs.
#
# Usage: generate-workload-tfvars.sh PROJECTS_DIR OUTPUT_FILE
# Env: APP_NAME, APP_ENV, PROJECT_ID, REGION, LOG_LEVEL, SUBNET_CIDR,
#      MEMORYSTORE_MEMORY_SIZE_GB, REDIS_CLOUD_HOST, REDIS_CLOUD_PORT,
#      REDIS_CLOUD_DB, FRONTEND_DOMAIN, ARTIFACTS_BUCKET

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 PROJECTS_DIR OUTPUT_FILE" >&2
  exit 1
fi

PROJECTS_DIR="$1"
OUTPUT_FILE="$2"

if [[ ! -d "${PROJECTS_DIR}" ]]; then
  echo "generate-workload-tfvars: projects dir not found: ${PROJECTS_DIR}" >&2
  exit 1
fi

hcl_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  printf '"%s"' "${value}"
}

tf_output() {
  local name="$1"
  terraform -chdir="${PROJECTS_DIR}" output -raw "${name}"
}

require_tf_output() {
  local name="$1"
  local value

  value="$(tf_output "${name}" 2>/dev/null || true)"
  if [[ -z "${value}" ]]; then
    echo "generate-workload-tfvars: required project output '${name}' is empty; is the projects stack deployed?" >&2
    exit 1
  fi

  printf '%s' "${value}"
}

PROJECT_NUMBER="$(require_tf_output project_number)"
FUNCTIONS_SA_EMAIL="$(require_tf_output functions_sa_email)"
API_GATEWAY_RUNTIME_SA_EMAIL="$(require_tf_output api_gateway_runtime_sa_email)"
EVENTARC_TRIGGER_SA_EMAIL="$(require_tf_output eventarc_trigger_sa_email)"
MEMORYSTORE_AUTH_SECRET_ID="$(require_tf_output memorystore_auth_secret_id)"
REDIS_CLOUD_CREDENTIALS_SECRET_ID="$(require_tf_output redis_cloud_credentials_secret_id)"

mkdir -p "$(dirname "${OUTPUT_FILE}")"

{
  printf 'app_name = %s\n' "$(hcl_string "${APP_NAME:-cloudshortener}")"
  printf 'app_env = %s\n' "$(hcl_string "${APP_ENV:-dev}")"
  printf 'region = %s\n' "$(hcl_string "${REGION:-europe-west1}")"
  printf 'project_id = %s\n' "$(hcl_string "${PROJECT_ID:?PROJECT_ID is required}")"
  printf 'project_number = %s\n' "$(hcl_string "${PROJECT_NUMBER}")"
  printf 'functions_sa_email = %s\n' "$(hcl_string "${FUNCTIONS_SA_EMAIL}")"
  printf 'api_gateway_runtime_sa_email = %s\n' "$(hcl_string "${API_GATEWAY_RUNTIME_SA_EMAIL}")"
  printf 'eventarc_trigger_sa_email = %s\n' "$(hcl_string "${EVENTARC_TRIGGER_SA_EMAIL}")"
  printf 'memorystore_auth_secret_id = %s\n' "$(hcl_string "${MEMORYSTORE_AUTH_SECRET_ID}")"
  printf 'log_level = %s\n' "$(hcl_string "${LOG_LEVEL:-INFO}")"
  printf 'subnet_cidr = %s\n' "$(hcl_string "${SUBNET_CIDR:-10.0.1.0/24}")"
  printf 'memorystore_memory_size_gb = %s\n' "${MEMORYSTORE_MEMORY_SIZE_GB:-1}"
  printf 'redis_cloud_port = %s\n' "${REDIS_CLOUD_PORT:-6379}"
  printf 'redis_cloud_db = %s\n' "${REDIS_CLOUD_DB:-0}"
  printf 'redis_cloud_credentials_secret = %s\n' "$(hcl_string "${REDIS_CLOUD_CREDENTIALS_SECRET_ID}")"

  if [[ -n "${REDIS_CLOUD_HOST:-}" ]]; then
    printf 'redis_cloud_host = %s\n' "$(hcl_string "${REDIS_CLOUD_HOST}")"
  fi

  if [[ -n "${FRONTEND_DOMAIN:-}" ]]; then
    printf 'frontend_domain = %s\n' "$(hcl_string "${FRONTEND_DOMAIN}")"
  fi

  if [[ -n "${ARTIFACTS_BUCKET:-}" ]]; then
    printf 'artifacts_bucket = %s\n' "$(hcl_string "${ARTIFACTS_BUCKET}")"
  fi
} >"${OUTPUT_FILE}"

echo "generate-workload-tfvars: wrote ${OUTPUT_FILE}"
