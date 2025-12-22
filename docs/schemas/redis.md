# Redis Data Store Schema — `cloudshortener`

This document defines the **authoritative Redis key schema** used by the
`cloudshortener` application.

## Global Key Prefix

All keys listed below are **relative** to the following prefix:

`cloudshortener:{env}`

Examples:
- `cloudshortener:local:`
- `cloudshortener:dev:`
- `cloudshortener:prod:`

## Key Schema

| Key Pattern | Redis Type | Description | Written By | Read By | Notes |
|------------|------------|-------------|------------|---------|-------|
| `links:counter` | `string (int)` | Global counter used for shortcode generation | `shorten_url` | `shorten_url` | Monotonic, never reset |
| `links:{shortcode}:url` | `string` | Target URL for a shortened link | `shorten_url` | `redirect_url` | Required for a valid shortcode |
| `links:{shortcode}:hits:{YYYY-MM}` | `string (int)` | Monthly redirect counter | `redirect_url` | analytics | Lazily created per month |
| `users:{user_id}:quota:{YYYY-MM}` | `string (int)` | Monthly link-creation quota counter per user | `shorten_url` | `shorten_url` | Missing key = zero usage |
