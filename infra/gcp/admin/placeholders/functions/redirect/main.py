"""Placeholder Cloud Function for Terraform wiring — not production logic."""

import json

import functions_framework

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Authorization, Content-Type",
}


@functions_framework.http
def redirect_url(request):
    """Hardcoded 302; OpenAPI expects empty JSON body and Location header."""
    if request.method == "OPTIONS":
        return ("", 204, CORS)

    headers = {
        **CORS,
        "Location": "https://example.com",
        "Content-Type": "application/json",
    }
    return (json.dumps({}), 302, headers)
