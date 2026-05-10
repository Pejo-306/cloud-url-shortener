#!/usr/bin/env bash
# Add a new Secret Manager secret version holding Redis Cloud credentials as JSON:
# {"username":"...","password":"..."}
#
# Usage: seed-redis-cloud-secret.sh PROJECT_ID APP_NAME APP_ENV REDIS_CLOUD_USER REDIS_CLOUD_PASS

set -euo pipefail

if [[ $# -lt 5 ]]; then
  echo "usage: $0 PROJECT_ID APP_NAME APP_ENV REDIS_CLOUD_USER REDIS_CLOUD_PASS" >&2
  exit 1
fi

PROJECT_ID="$1"
APP_NAME="$2"
APP_ENV="$3"
REDIS_CLOUD_USER="$4"
REDIS_CLOUD_PASS="$5"

SECRET_NAME="${APP_NAME}-${APP_ENV}-secret-redis-credentials"

if [[ -z "${REDIS_CLOUD_USER}" ]] || [[ -z "${REDIS_CLOUD_PASS}" ]]; then
  echo "seed-redis-cloud-secret: REDIS_CLOUD_USER and REDIS_CLOUD_PASS must be set" >&2
  exit 1
fi

payload="$(printf '{"username":"%s","password":"%s"}' "$REDIS_CLOUD_USER" "$REDIS_CLOUD_PASS")"

echo "seed-redis-cloud-secret: adding version to secret ${SECRET_NAME} in ${PROJECT_ID}"
printf '%s' "${payload}" | gcloud secrets versions add "${SECRET_NAME}" \
  --project="${PROJECT_ID}" \
  --data-file=-
