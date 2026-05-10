#!/usr/bin/env bash
# Enable bootstrap APIs on an env GCP project.
#
# Usage: enable-bootstrap-apis.sh PROJECT_ID

set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "usage: $0 PROJECT_ID" >&2
  exit 1
fi

PROJECT_ID="$1"

required_services=(
  "serviceusage.googleapis.com"
)

for service in "${required_services[@]}"; do
  echo "enable-bootstrap-apis: enabling ${service} on project ${PROJECT_ID}"
  gcloud services enable "${service}" --project="${PROJECT_ID}"
done

echo "enable-bootstrap-apis: waiting for APIs to report ENABLED..."
deadline=$((SECONDS + 900))
sleep_interval=30

while (( SECONDS < deadline )); do
  enabled_services="$(gcloud services list \
    --project="${PROJECT_ID}" \
    --enabled \
    --format='value(config.name)' \
    --verbosity=warning 2>/dev/null || true)"

  missing=()
  for service in "${required_services[@]}"; do
    found=false
    while IFS= read -r enabled_service; do
      if [[ "${enabled_service}" == "${service}" ]]; then
        found=true
        break
      fi
    done <<< "${enabled_services}"

    if [[ "${found}" != true ]]; then
      missing+=("${service}")
    fi
  done

  if [[ "${#missing[@]}" -eq 0 ]]; then
    echo "enable-bootstrap-apis: required APIs are ENABLED"
    break
  fi

  echo "enable-bootstrap-apis: waiting on ${missing[*]} (retry in ${sleep_interval}s)"
  sleep "${sleep_interval}"
done

if [[ "${#missing[@]}" -ne 0 ]]; then
  echo "enable-bootstrap-apis: timeout waiting for API enable propagation" >&2
  exit 1
fi
