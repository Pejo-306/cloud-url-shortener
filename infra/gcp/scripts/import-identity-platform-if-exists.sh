#!/usr/bin/env bash
# Import the project Identity Platform config into Terraform state if it exists.
#
# Identity Platform is a project-level singleton. Terraform can create and
# manage its config, but GCP does not actually disable Identity Platform when
# the Terraform resource is destroyed. A deploy -> destroy -> deploy cycle can
# therefore leave the config enabled in GCP but absent from Terraform state,
# causing the next apply to fail with "Identity Platform has already been
# enabled for this project." Importing before the full projects apply makes
# both fresh projects and reused projects idempotent.
#
# Usage: import-identity-platform-if-exists.sh PROJECTS_DIR VAR_FILE

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 PROJECTS_DIR VAR_FILE" >&2
  exit 1
fi

PROJECTS_DIR="$1"
VAR_FILE="$2"
RESOURCE_ADDRESS="google_identity_platform_config.default"

if [[ "${VAR_FILE}" = /* ]]; then
  readable_var_file="${VAR_FILE}"
else
  readable_var_file="${PROJECTS_DIR}/${VAR_FILE}"
fi

if [[ ! -f "${readable_var_file}" ]]; then
  echo "import-identity-platform-if-exists: tfvars file not found: ${readable_var_file}" >&2
  exit 1
fi

project_id="$(
  awk '
    /^[[:space:]]*project_id[[:space:]]*=/ {
      sub(/^[^=]*=[[:space:]]*/, "", $0)
      sub(/^"/, "", $0)
      sub(/"[[:space:]]*$/, "", $0)
      print
      exit
    }
  ' "${readable_var_file}"
)"

if [[ -z "${project_id}" ]]; then
  echo "import-identity-platform-if-exists: project_id not found in ${readable_var_file}" >&2
  exit 1
fi

if terraform -chdir="${PROJECTS_DIR}" state show "${RESOURCE_ADDRESS}" >/dev/null 2>&1; then
  echo "import-identity-platform-if-exists: ${RESOURCE_ADDRESS} already in state, skipping"
  exit 0
fi

echo "import-identity-platform-if-exists: checking for existing Identity Platform config in ${project_id}"

if terraform -chdir="${PROJECTS_DIR}" import \
  -var-file="${VAR_FILE}" \
  "${RESOURCE_ADDRESS}" \
  "projects/${project_id}/config" >/dev/null 2>&1; then
  echo "import-identity-platform-if-exists: imported existing Identity Platform config"
else
  echo "import-identity-platform-if-exists: no existing config imported; Terraform apply will create it"
fi
