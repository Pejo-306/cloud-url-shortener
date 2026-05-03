"""Placeholder Cloud Function for Terraform wiring — not production logic."""

import json

import functions_framework

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
}


@functions_framework.http
def shorten_url(request):
    """Hardcoded shape matching OpenAPI ShortenSuccessResponse."""
    if request.method == "OPTIONS":
        return ("", 204, CORS)

    body = {
        "message": "PLACEHOLDER: shorten not implemented yet",
        "targetUrl": "https://example.com",
        "shortUrl": "https://example.com/abc12",
        "shortcode": "abc12",
        "userQuota": 0,
        "remainingQuota": 1000,
    }
    return (json.dumps(body), 200, {**CORS, "Content-Type": "application/json"})
