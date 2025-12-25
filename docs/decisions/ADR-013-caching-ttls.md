# ADR-013: Caching TTLs

## Status

Accepted

## Date

2025-12-25

## Context

The `cloudshortener` system caches it's configurations and some hot keys in
it's caching layer. Leaving cached keys without a TTL could lead to a stale cache,
risking manual intervention on configuration changes.

Relevant documents:
- Minimal redirect latency ([NFR-1](/docs/requirements.md#nfr-1-performance))
- Caching strategy ([ADR-007](/docs/decisions/ADR-007-caching-strategy.md))

## Decision

Use a multi-tiered TTL strategy for different data keys.

| Tier   | TTL          | Use Case                                |
|--------|--------------|-----------------------------------------|
| `HOT`  | `60 minutes` | Very frequently accessed shortcodes     |
| `WARM` | `24 hours`   | Somewhat frequently accessed shortcodes |
| `COOL` | `7 days`     | AppConfig documents                     |

`HOT` keys last only `60 minutes` and are primary used for very frequently accessed
shortcodes. These shortcodes are anticipated to be limitted by their link hit quota
within a few hours, hence the short timespan in the cache.

`WARM` keys are for shortcodes which are expected to hit their link hit quota within
a few days (up to a week).

`COOL` keys are for other cached information which changes infrequently (1-5 times
per month), e.g. AppConfig documents.

## Alternatives Considered

### 1. No TTLs

**Pros**
- No implementation needed

**Cons**
- Will lead to stale configuration documents or overpopulating the cache and reliance
  on an LRU algorithm

**Rejected** due to staleness and overpopulation concerns.

## Consequences

### Positive
- Prevents cache staleness and cache overpopulation

### Negative
- Introduces some additional implementation complexity
