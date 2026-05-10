#!/usr/bin/env bash
# Import an existing GCP project into Terraform state if it exists.
#
# After a destroy with deletion_policy=ABANDON, the project remains in GCP
# but is absent from Terraform state. A subsequent deploy would fail with
# "409 alreadyExists" when trying to create it. Importing before the
# targeted create step makes deploy -> destroy -> deploy idempotent.
#
# Usage: import-project-if-exists.sh PROJECTS_DIR VAR_FILE PROJECT_ID

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 PROJECTS_DIR VAR_FILE PROJECT_ID" >&2
  exit 1
fi

PROJECTS_DIR="$1"
VAR_FILE="$2"
PROJECT_ID="$3"
RESOURCE_ADDRESS="google_project.this[0]"

if terraform -chdir="${PROJECTS_DIR}" state show "${RESOURCE_ADDRESS}" >/dev/null 2>&1; then
  echo "import-project-if-exists: ${RESOURCE_ADDRESS} already in state, skipping"
  exit 0
fi

if ! gcloud projects describe "${PROJECT_ID}" --format='value(projectId)' --verbosity=error >/dev/null 2>&1; then
  echo "import-project-if-exists: project ${PROJECT_ID} does not exist in GCP, skipping"
  exit 0
fi

echo "import-project-if-exists: importing existing project ${PROJECT_ID}"

if terraform -chdir="${PROJECTS_DIR}" import \
  -var-file="${VAR_FILE}" \
  "${RESOURCE_ADDRESS}" \
  "${PROJECT_ID}" >/dev/null 2>&1; then
  echo "import-project-if-exists: imported existing project ${PROJECT_ID}"
else
  echo "import-project-if-exists: failed to import existing project ${PROJECT_ID}" >&2
  exit 1
fi
