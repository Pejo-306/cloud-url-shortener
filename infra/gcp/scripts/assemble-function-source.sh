#!/usr/bin/env bash
# Assemble deployable Cloud Function source directories from backend code.
#
# Usage: assemble-function-source.sh CLOUD_FUNCTIONS_SOURCE_DIR

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 CLOUD_FUNCTIONS_SOURCE_DIR" >&2
  exit 1
fi

CLOUD_FUNCTIONS_SOURCE_DIR="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GCP_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${GCP_DIR}/../.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
CLOUDSHORTENER_PACKAGE_DIR="${BACKEND_DIR}/cloudshortener"
GCP_FUNCTIONS_DIR="${CLOUDSHORTENER_PACKAGE_DIR}/cloud/gcp/cloud_functions"
PLACEHOLDER_FUNCTIONS_DIR="${GCP_DIR}/admin/placeholders/functions"

require_file() {
  local file="$1"

  if [[ ! -f "${file}" ]]; then
    echo "assemble-function-source: file not found: ${file}" >&2
    exit 1
  fi
}

require_dir() {
  local dir="$1"

  if [[ ! -d "${dir}" ]]; then
    echo "assemble-function-source: dir not found: ${dir}" >&2
    exit 1
  fi
}

copy_python_function() {
  local function_name="$1"
  local source_dir="${GCP_FUNCTIONS_DIR}/${function_name}"
  local target_dir="${CLOUD_FUNCTIONS_SOURCE_DIR}/${function_name}"

  require_file "${source_dir}/main.py"
  require_file "${source_dir}/requirements.txt"
  require_dir "${CLOUDSHORTENER_PACKAGE_DIR}"

  echo "assemble-function-source: assembling ${function_name} from backend source"
  rm -rf "${target_dir}"
  mkdir -p "${target_dir}"

  cp -p "${source_dir}/main.py" "${target_dir}/main.py"
  cp -p "${source_dir}/requirements.txt" "${target_dir}/requirements.txt"
  rsync -a --delete --exclude='__pycache__' "${CLOUDSHORTENER_PACKAGE_DIR}/" "${target_dir}/cloudshortener/"
}

copy_placeholder_function() {
  local function_name="$1"
  local source_dir="${PLACEHOLDER_FUNCTIONS_DIR}/${function_name}"
  local target_dir="${CLOUD_FUNCTIONS_SOURCE_DIR}/${function_name}"

  require_dir "${source_dir}"

  echo "assemble-function-source: assembling ${function_name} from placeholders"
  rm -rf "${target_dir}"
  mkdir -p "${target_dir}"
  rsync -a --delete --exclude='__pycache__' "${source_dir}/" "${target_dir}/"
}

mkdir -p "${CLOUD_FUNCTIONS_SOURCE_DIR}"

copy_python_function "redirect"
copy_python_function "shorten"
copy_placeholder_function "warm"
