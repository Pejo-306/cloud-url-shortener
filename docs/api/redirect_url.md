# `GET /{shortcode}` — Redirect to target URL

Resolves a shortcode, applies monthly hit quota, and redirects the client to the stored target URL.

## Authentication

**None.** Public endpoint.

## Path parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `shortcode` | string | Yes | Shortcode from the URL path |

## Success response (`302`)

| Aspect | Value |
|--------|--------|
| Header `Location` | Resolved target URL |
| Body | `{}` (empty JSON object) |

## Responses

| HTTP status | Error code | Description |
|-------------|------------|-------------|
| `302` | — | Redirect to target URL |
| `400` | `MISSING_SHORTCODE` | Missing `shortcode` in path |
| `400` | `SHORT_URL_NOT_FOUND` | Short URL not found |
| `429` | `LINK_QUOTA_EXCEEDED` | Monthly hit quota for the link exceeded |
| `500` | — | Unhandled internal server error |

On error responses, JSON may include `errorCode` (camelCase) when an application code applies. Error codes are not guaranteed stable; prefer HTTP status.

## Special headers (`429`)

| Header | Value |
|--------|--------|
| `Retry-After` | Seconds until quota reset (beginning of next month) |
| `Content-Type` | `application/json` |
