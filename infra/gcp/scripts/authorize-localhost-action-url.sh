#!/usr/bin/env bash
# Add localhost to Identity Platform authorized domains.
#
# This lets local development redirects use localhost without enabling any
# custom email action URL.
#
# Usage: authorize-localhost-action-url.sh PROJECT_ID

set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "usage: $0 PROJECT_ID" >&2
  exit 1
fi

PROJECT_ID="$1"
LOCAL_DOMAIN="localhost"
API_URL="https://identitytoolkit.googleapis.com/admin/v2/projects/${PROJECT_ID}/config"

TOKEN="$(gcloud auth print-access-token)"

echo "authorize-localhost-action-url: reading authorized domains for project ${PROJECT_ID}"

CURRENT_DOMAINS="$(curl -sSf \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  "${API_URL}" | jq '.authorizedDomains // []')"

UPDATED_DOMAINS="$(printf '%s' "${CURRENT_DOMAINS}" | jq --arg domain "${LOCAL_DOMAIN}" \
  'if any(. == $domain) then . else . + [$domain] end')"

if [[ "$(printf '%s' "${CURRENT_DOMAINS}" | jq -S .)" == "$(printf '%s' "${UPDATED_DOMAINS}" | jq -S .)" ]]; then
  echo "authorize-localhost-action-url: localhost already authorized, skipping"
  exit 0
fi

AUTHORIZED_DOMAINS_BODY="$(jq -n --argjson domains "${UPDATED_DOMAINS}" '{
  "authorizedDomains": $domains
}')"

echo "authorize-localhost-action-url: ensuring localhost is authorized"

curl -sSf -X PATCH \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d "${AUTHORIZED_DOMAINS_BODY}" \
  "${API_URL}?updateMask=authorizedDomains" \
  >/dev/null

echo "authorize-localhost-action-url: done"
