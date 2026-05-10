#!/usr/bin/env bash
# Upload pre-built Cloud Function ZIP files to the env-scoped GCS artifacts path.
#
# Usage: upload-function-zips.sh CLOUD_FUNCTIONS_ARTIFACTS_DIR ARTIFACTS_BUCKET APP_ENV

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: $0 CLOUD_FUNCTIONS_ARTIFACTS_DIR ARTIFACTS_BUCKET APP_ENV" >&2
  exit 1
fi

CLOUD_FUNCTIONS_ARTIFACTS_DIR="$1"
ARTIFACTS_BUCKET="$2"
APP_ENV="$3"

if [[ ! -d "${CLOUD_FUNCTIONS_ARTIFACTS_DIR}" ]]; then
  echo "upload-function-zips: artifacts dir not found: ${CLOUD_FUNCTIONS_ARTIFACTS_DIR}" >&2
  echo "upload-function-zips: run make build first" >&2
  exit 1
fi

shopt -s nullglob
zip_files=("${CLOUD_FUNCTIONS_ARTIFACTS_DIR}"/*.zip)

if [[ "${#zip_files[@]}" -eq 0 ]]; then
  echo "upload-function-zips: no function zips found in ${CLOUD_FUNCTIONS_ARTIFACTS_DIR}" >&2
  echo "upload-function-zips: run make build first" >&2
  exit 1
fi

for zip_file in "${zip_files[@]}"; do
  echo "upload-function-zips: uploading ${zip_file} to gs://${ARTIFACTS_BUCKET}/${APP_ENV}/cloud-functions/"
  gcloud storage cp "${zip_file}" "gs://${ARTIFACTS_BUCKET}/${APP_ENV}/cloud-functions/"
done
