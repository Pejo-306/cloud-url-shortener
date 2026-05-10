#!/usr/bin/env bash
# Poll until Cloud Billing is enabled on an env GCP project.
#
# Usage: poll-cloud-billing.sh PROJECT_ID

set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "usage: $0 PROJECT_ID" >&2
  exit 1
fi

PROJECT_ID="$1"

echo "poll-cloud-billing: waiting for billing to report ENABLED..."
deadline=$((SECONDS + 900))
sleep_interval=30

while (( SECONDS < deadline )); do
  billing_enabled="$(gcloud billing projects describe "${PROJECT_ID}" \
    --format='value(billingEnabled)' \
    --verbosity=warning 2>/dev/null || true)"

  if [[ "${billing_enabled}" == "True" ]]; then
    echo "poll-cloud-billing: billing is ENABLED"
    exit 0
  fi

  echo "poll-cloud-billing: waiting on billing propagation (retry in ${sleep_interval}s)"
  sleep "${sleep_interval}"
done

echo "poll-cloud-billing: timeout waiting for billing propagation" >&2
exit 1
