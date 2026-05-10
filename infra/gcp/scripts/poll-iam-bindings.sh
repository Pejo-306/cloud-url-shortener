#!/usr/bin/env bash
# Poll until service accounts and project IAM bindings created by
# infra/gcp/projects/iam.tf are visible to gcloud.
#
# Usage: poll-iam-bindings.sh PROJECT_ID APP_ENV

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 PROJECT_ID APP_ENV" >&2
  exit 1
fi

PROJECT_ID="$1"
APP_ENV="$2"

accounts=(
  "cf-functions-${APP_ENV}@${PROJECT_ID}.iam.gserviceaccount.com"
  "api-gateway-${APP_ENV}@${PROJECT_ID}.iam.gserviceaccount.com"
  "cf-eventarc-trigger-${APP_ENV}@${PROJECT_ID}.iam.gserviceaccount.com"
)

project_number="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"

bindings=(
  "roles/logging.logWriter|serviceAccount:cf-functions-${APP_ENV}@${PROJECT_ID}.iam.gserviceaccount.com"
  "roles/eventarc.eventReceiver|serviceAccount:cf-eventarc-trigger-${APP_ENV}@${PROJECT_ID}.iam.gserviceaccount.com"
  "roles/cloudbuild.builds.builder|serviceAccount:${project_number}-compute@developer.gserviceaccount.com"
  "roles/eventarc.serviceAgent|serviceAccount:service-${project_number}@gcp-sa-eventarc.iam.gserviceaccount.com"
  "roles/pubsub.publisher|serviceAccount:service-${project_number}@gs-project-accounts.iam.gserviceaccount.com"
)

deadline=$((SECONDS + 900))
sleep_interval=30

has_binding() {
  local role="$1"
  local member="$2"

  [[ -n "$(gcloud projects get-iam-policy "${PROJECT_ID}" \
    --flatten='bindings[].members' \
    --filter="bindings.role=${role} AND bindings.members=${member}" \
    --format='value(bindings.role)' \
    --verbosity=error 2>/dev/null || true)" ]]
}

while (( SECONDS < deadline )); do
  all_ok=true

  for email in "${accounts[@]}"; do
    if ! gcloud iam service-accounts describe "${email}" \
      --project="${PROJECT_ID}" \
      --verbosity=error >/dev/null 2>&1; then
      all_ok=false
      echo "poll-iam-bindings: waiting for SA ${email}..."
      break
    fi
  done

  if [[ "${all_ok}" == true ]]; then
    for binding in "${bindings[@]}"; do
      role="${binding%%|*}"
      member="${binding#*|}"

      if ! has_binding "${role}" "${member}"; then
        all_ok=false
        echo "poll-iam-bindings: waiting for ${role} -> ${member}..."
        break
      fi
    done
  fi

  if $all_ok; then
    echo "poll-iam-bindings: service accounts and IAM bindings are visible"
    exit 0
  fi

  sleep "${sleep_interval}"
done

echo "poll-iam-bindings: timeout waiting for IAM propagation" >&2
exit 1
