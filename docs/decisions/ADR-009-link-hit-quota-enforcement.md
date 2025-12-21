# ADR-009: Link Hit Quota Enforcement Strategy

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system enforces a **per-link hit quota** that limits how many
times a short URL may be resolved within a calendar month.

Relevant requirements and constraints:
- Each short URL may be accessed up to **10,000 times per month**
  ([FR-5](/docs/requirements.md#fr-5-link-hit-quotas))
- Redirect requests are **latency-critical** and **read-heavy**
- Serverless, stateless compute model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Redis Cloud is the primary datastore ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))
- Minimize operational and architectural complexity ([C-3](/docs/requirements.md#c-3-team-size))

Quota enforcement occurs on the **redirect (read) path** and must:
- Prevent abuse and excessive traffic
- Be extremely fast
- Scale horizontally
- Remain correct under high concurrency

## Decision

Enforce link hit quotas using **Redis-based atomic counters with TTL**, scoped per
shortcode and per calendar month.

Each short URL has a dedicated hit counter key of the form:

```
links:{shortcode}:hits:{YYYY-MM}
```

The quota is enforced directly within the redirect Lambda function using Redis
atomic operations.

## Rationale

### Why Redis-Based Counters

Redis provides:
- Atomic increment and decrement operations
- Built-in TTL support
- O(1) command execution
- Strong consistency for single-key operations

This allows quota enforcement to occur inline with redirect resolution without
introducing additional coordination or external services.

### Why Per-Month Keys with TTL

Using time-scoped keys:
- Eliminates the need for scheduled reset jobs
- Automatically resets hit quotas at month boundaries
- Keeps historical data ephemeral
- Reduces operational complexity

TTL-based expiration aligns naturally with monthly quota semantics and the
system’s retention-based design.

## Quota Enforcement Algorithm

At a high level, link hit quota enforcement follows this flow:

1. Determine the current calendar month (`YYYY-MM`)
2. Construct the link hit quota key
3. Atomically decrement the remaining hit count
4. Validate the resulting value
5. Allow or reject the redirect accordingly

### Redis Command Semantics

The core Redis operations used are:

```java
DECR links:{shortcode}:hits:{YYYY-MM}
EXPIRE links:{shortcode}:hits:{YYYY-MM} <ttl>
```

Key properties:
- `DECR` is atomic
- The first access initializes the counter
- TTL ensures automatic monthly reset

The hit counter is initialized to the maximum monthly hit limit when first
created.

TTL is applied only when the key is first created to avoid resetting expiration
on every access.

## Lambda-Level Pseudocode

Conceptually, link hit quota enforcement can be expressed as:

```c++
key = "links:{shortcode}:hits:{current_month}"

remaining_hits = DECR(key)

if remaining_hits == MAX_MONTHLY_HITS - 1:
    EXPIRE(key, end_of_month_ttl)

if remaining_hits < 0:
    reject request with HTTP 429
else:
    proceed with redirect
```

This logic executes in constant time and does not require locks or transactions.

## Concurrency and Correctness

- Redis guarantees atomicity for single-key operations
- Concurrent redirect requests are serialized at the Redis level
- At most one request can cross the quota boundary

Under extreme concurrency, a small amount of best-effort tolerance is accepted
as defined by system requirements.

## Alternatives Considered

### 1. Tracking Hits in a Relational or Analytical Store

**Pros**
- Rich analytics capabilities
- Long-term history

**Cons**
- Higher latency
- Not suitable for inline enforcement
- Overkill for simple counters

**Rejected** due to performance and complexity concerns.

### 2. Scheduled Reset Jobs

**Pros**
- Explicit reset control

**Cons**
- Additional operational complexity
- Failure-prone
- Unnecessary given TTL support

**Rejected** in favor of TTL-based expiration.

## Failure Considerations

- Redis unavailability prevents hit quota enforcement
- In such cases, the system may fail closed (reject redirects) to prevent abuse
- Hit quota enforcement is isolated to the redirect path

Failure behavior is consistent with overall system resilience goals.

## Consequences

### Positive
- Fast, inline quota enforcement
- No background jobs or schedulers
- Automatic monthly reset
- Strong concurrency guarantees
- Minimal latency impact on redirect path

### Negative
- Best-effort enforcement under extreme contention
- Ephemeral quota state
- Requires careful TTL alignment with calendar boundaries

## Impact

This decision directly influences:
- Redirect-path latency and correctness
- Abuse prevention strategy
- Redis key design and memory usage
- Failure behavior under partial outages
- Scalability characteristics of the read path

Future changes to hit limits or time granularity may require revisiting key
structure or enforcement logic.
