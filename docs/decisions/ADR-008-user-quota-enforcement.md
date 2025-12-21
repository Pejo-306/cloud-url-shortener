# ADR-008: User Quota Enforcement Strategy

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system enforces a **per-user quota** that limits the number
of short URLs a user may create per calendar month.

Relevant requirements and constraints:
- Each authenticated user may create up to **20 short URLs per month**
  ([FR-4](/docs/requirements.md#fr-4-user-quotas))
- The system is read-heavy but write operations must remain correct
- Serverless, stateless compute model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Redis Cloud is the primary datastore ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))
- Minimize operational and architectural complexity ([C-3](/docs/requirements.md#c-3-team-size))

Quota enforcement occurs on the **write path** and must:
- Prevent abuse
- Be fast and deterministic
- Scale horizontally
- Avoid introducing race conditions under concurrency

## Decision

Enforce user quotas using **Redis-based atomic counters with TTL**, scoped per
user and per calendar month.

Each user has a dedicated quota key of the form:

```
users:{user_id}:quota:{YYYY-MM}
```

The quota is enforced directly within the URL shortening Lambda function using
Redis atomic operations.

## Rationale

### Why Redis-Based Counters

Redis provides:
- Atomic increment operations
- Built-in TTL support
- O(1) command execution
- Strong consistency for single-key operations

This makes Redis counters a natural fit for enforcing quotas in a distributed,
serverless environment without introducing additional coordination mechanisms.

### Why Per-Month Keys with TTL

Using time-scoped keys:
- Eliminates the need for scheduled reset jobs
- Automatically resets quotas at month boundaries
- Keeps historical data ephemeral
- Reduces operational complexity

TTL-based expiration aligns cleanly with:
- Monthly quota semantics
- Stateless compute
- Retention-based system design

## Quota Enforcement Algorithm

At a high level, quota enforcement follows this flow:

1. Determine the current calendar month (`YYYY-MM`)
2. Construct the user quota key
3. Atomically increment the counter
4. Validate the resulting value against the quota limit
5. Allow or reject the request accordingly

### Redis Command Semantics

The core Redis operations used are:

```java
INCR users:{user_id}:quota:{YYYY-MM}
EXPIRE users:{user_id}:quota:{YYYY-MM} <ttl>
```

Key properties:
- `INCR` is atomic
- The first increment creates the key if it does not exist
- TTL ensures automatic quota reset

TTL is applied only when the key is first created to avoid resetting expiration
on every increment.

### Lambda-Level Pseudocode

Conceptually, quota enforcement can be expressed as:

```c++
key = "users:{user_id}:quota:{current_month}"

current_count = INCR(key)

if current_count == 1:
    EXPIRE(key, end_of_month_ttl)

if current_count > MAX_MONTHLY_QUOTA:
    reject request with HTTP 429
else:
    proceed with URL creation
```

This logic is safe under concurrency and does not require locks or transactions.

## Concurrency and Correctness

- Redis guarantees atomicity for single-key operations
- Concurrent requests from the same user are serialized at the Redis level
- At most one request can cross the quota boundary

A small amount of best-effort tolerance is accepted under extreme concurrency,
as allowed by system requirements.

## Alternatives Considered

### 1. Database-Backed Quota Tables

**Pros**
- Explicit quota history
- Strong consistency guarantees

**Cons**
- Higher latency
- Requires schema management
- Overkill for simple counters

**Rejected** due to complexity and performance overhead.

### 2. Scheduled Reset Jobs

**Pros**
- Explicit reset control

**Cons**
- Requires cron jobs or schedulers
- Additional operational burden
- Failure-prone

**Rejected** in favor of TTL-based expiration.

## Failure Considerations

- Redis unavailability prevents quota checks
- In such cases, the system may fail closed (reject writes) to prevent abuse
- Quota enforcement is not applied to the redirect (read) path

Failure handling strategies are aligned with overall system resilience goals.

## Consequences

### Positive
- Simple and deterministic quota enforcement
- No background jobs or schedulers
- Automatic monthly reset
- Strong concurrency guarantees
- Low latency and high scalability

### Negative
- Quota enforcement is best-effort under extreme contention
- Quota state is ephemeral and not persisted long-term
- TTL calculation must be correct to align with calendar boundaries

## Impact

This decision directly influences:
- Write-path correctness
- Abuse prevention
- Redis key design
- Failure behavior under partial outages
- System scalability characteristics

Future changes to quota limits or time granularity may require revisiting key
structure or TTL calculation logic.
