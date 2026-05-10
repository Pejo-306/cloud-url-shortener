#!/usr/bin/env bash
# Configure Identity Platform password policy via the Admin REST API.
#
# The Terraform google/google-beta providers don't expose passwordPolicyConfig
# on google_identity_platform_config. This script PATCHes it directly for
# Cognito parity (min length 6, no character-class requirements).
#
# Usage: configure-identity-platform-password-policy.sh PROJECT_ID

set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "usage: $0 PROJECT_ID" >&2
  exit 1
fi

PROJECT_ID="$1"

POLICY_BODY='{
  "passwordPolicyConfig": {
    "passwordPolicyEnforcementState": "ENFORCE",
    "forceUpgradeOnSignin": false,
    "passwordPolicyVersions": [{
      "customStrengthOptions": {
        "minPasswordLength": 6,
        "containsLowercaseCharacter": false,
        "containsUppercaseCharacter": false,
        "containsNumericCharacter": false,
        "containsNonAlphanumericCharacter": false
      }
    }]
  }
}'

TOKEN="$(gcloud auth print-access-token)"

echo "configure-identity-platform-password-policy: setting password policy on project ${PROJECT_ID}"

curl -sSf -X PATCH \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "x-goog-user-project: ${PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d "${POLICY_BODY}" \
  "https://identitytoolkit.googleapis.com/admin/v2/projects/${PROJECT_ID}/config?updateMask=passwordPolicyConfig" \
  >/dev/null

echo "configure-identity-platform-password-policy: done"
