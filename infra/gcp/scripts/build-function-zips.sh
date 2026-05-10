#!/usr/bin/env bash
# Build Cloud Function source ZIP files from one directory per function.
#
# Usage: build-function-zips.sh CLOUD_FUNCTIONS_SOURCE_DIR CLOUD_FUNCTIONS_ARTIFACTS_DIR

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 CLOUD_FUNCTIONS_SOURCE_DIR CLOUD_FUNCTIONS_ARTIFACTS_DIR" >&2
  exit 1
fi

CLOUD_FUNCTIONS_SOURCE_DIR="$1"
CLOUD_FUNCTIONS_ARTIFACTS_DIR="$2"

if [[ ! -d "${CLOUD_FUNCTIONS_SOURCE_DIR}" ]]; then
  echo "build-function-zips: source dir not found: ${CLOUD_FUNCTIONS_SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "${CLOUD_FUNCTIONS_ARTIFACTS_DIR}"

shopt -s nullglob
function_dirs=("${CLOUD_FUNCTIONS_SOURCE_DIR}"/*)

for function_dir in "${function_dirs[@]}"; do
  if [[ -d "${function_dir}" ]]; then
    function_name="$(basename "${function_dir}")"
    zip_file="${CLOUD_FUNCTIONS_ARTIFACTS_DIR}/${function_name}.zip"
    zip_abs="$(pwd)/${zip_file}"

    echo "build-function-zips: building ${zip_file}"
    rm -f "${zip_file}"
    (cd "${function_dir}" && zip -qr "${zip_abs}" .)
  fi
done
