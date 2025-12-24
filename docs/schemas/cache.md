# Cache Key Schema — `cloudshortener`

This document defines the Redis key schema used for **application-level caching**
in the `cloudshortener` system.

## Global Cache Prefix

All keys listed below are **relative** to the following prefix:

`cache:cloudshortener:{dev}`

Examples:
- `cache:cloudshortener:local:`
- `cache:cloudshortener:dev:`
- `cache:cloudshortener:prod:`

## Key Schema

| Key Pattern | Redis Type | Description | Written By | Read By | Notes |
|------------|------------|-------------|------------|---------|-------|
| `appconfig:v1` | `string` | Cached AppConfig configuration payload (versioned) | backend lambdas | backend lambdas | Canonical cached config |
| `appconfig:latest` | `string` | Latest AppConfig configuration payload | backend lambdas | backend lambdas | Duplicate of latest version for fast access |
| `appconfig:latest:metadata` | `string` | Metadata for latest AppConfig payload | backend lambdas | backend lambdas | Duplicate of latest version metadata for fast access |
| `appconfig:v1:metadata` | `string` | Metadata for cached AppConfig payload | backend lambdas | backend lambdas | Used for cache validation |
