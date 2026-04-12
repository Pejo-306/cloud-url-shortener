# `POST /v1/shorten` — Shorten a URL

Creates a shortened URL for an authenticated user and returns the new short URL and quota state.

## Authentication

**Required.** API Gateway uses a Cognito authorizer; the handler reads the Cognito user id from JWT claim `sub`.

## Request body

JSON object. Either field name is accepted; the first non-empty value wins.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `targetUrl` / `target_url` | string | Yes | Original URL to shorten |

## Success response (`200`)

JSON body:

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Human-readable success message |
| `targetUrl` | string | Original URL from the request |
| `shortUrl` | string | Full short URL (scheme + host + path) |
| `shortcode` | string | Generated shortcode |
| `userQuota` | number | User’s link-generation count after this create |
| `remainingQuota` | number | Remaining monthly link-generation quota |

## Responses

| HTTP status | Error code | Description |
|-------------|------------|-------------|
| `200` | — | Short URL created |
| `400` | `INVALID_JSON` | Request body is not valid JSON |
| `400` | `MISSING_TARGET_URL` | Missing or empty `target_url` / `targetUrl` |
| `401` | `MISSING_USER_ID` | Missing Cognito `sub` in JWT claims |
| `409` | `SHORT_URL_ALREADY_EXISTS` | Short URL already exists |
| `429` | `LINK_QUOTA_EXCEEDED` | Monthly link-generation quota exceeded |
| `500` | — | Unhandled internal server error |

On error responses, JSON may include `errorCode` (camelCase) when an application code applies. Error codes are not guaranteed stable; prefer HTTP status.
