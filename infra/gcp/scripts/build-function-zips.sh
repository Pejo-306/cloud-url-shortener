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
HASHES_FILE="${CLOUD_FUNCTIONS_ARTIFACTS_DIR}/hashes.env"

if [[ ! -d "${CLOUD_FUNCTIONS_SOURCE_DIR}" ]]; then
  echo "build-function-zips: source dir not found: ${CLOUD_FUNCTIONS_SOURCE_DIR}" >&2
  exit 1
fi

mkdir -p "${CLOUD_FUNCTIONS_ARTIFACTS_DIR}"
rm -f "${CLOUD_FUNCTIONS_ARTIFACTS_DIR}"/*.zip
rm -f "${HASHES_FILE}"

shopt -s nullglob
function_dirs=("${CLOUD_FUNCTIONS_SOURCE_DIR}"/*)

for function_dir in "${function_dirs[@]}"; do
  if [[ -d "${function_dir}" ]]; then
    function_name="$(basename "${function_dir}")"
    zip_file="${CLOUD_FUNCTIONS_ARTIFACTS_DIR}/${function_name}.zip"
    zip_abs="$(pwd)/${zip_file}"

    echo "build-function-zips: building ${zip_file}"
    rm -f "${zip_file}"
    (cd "${function_dir}" && find . -type f | LC_ALL=C sort | zip -q -X "${zip_abs}" -@)

    hash="$(shasum -a 256 "${zip_file}" | awk '{print substr($1, 1, 16)}')"
    printf '%s=%s\n' "${function_name}" "${hash}" >>"${HASHES_FILE}"
  fi
done

if [[ ! -s "${HASHES_FILE}" ]]; then
  echo "build-function-zips: no function source directories found in ${CLOUD_FUNCTIONS_SOURCE_DIR}" >&2
  exit 1
fi

echo "build-function-zips: wrote ${HASHES_FILE}"
