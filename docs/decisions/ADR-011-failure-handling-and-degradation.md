# ADR-011: Failure Handling and Degradation Strategy

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system is composed of multiple managed and external
dependencies, including:

- Redis Cloud (primary datastore) ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))
- AWS Lambda (serverless compute) ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- AWS AppConfig, Parameter Store, Secrets Manager ([ADR-006](/docs/decisions/ADR-006-configuration-management.md))
- AWS API Gateway with Cognito authorizers ([ADR-010](/docs/decisions/ADR-010-authentication-model.md))
- Caching layers ([ADR-007](/docs/decisions/ADR-007-caching-strategy.md))

Failures in distributed systems are inevitable. The system must therefore define
**explicit behavior** for when components are unavailable, slow, or inconsistent.

Relevant requirements and constraints:
- High availability is preferred, but not at the cost of correctness ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Abuse prevention and quota enforcement must remain reliable ([ADR-008](/docs/decisions/ADR-008-user-quota-enforcement.md), [ADR-009](/docs/decisions/ADR-009-link-hit-quota-enforcement.md))
- Redirect latency is critical; shortening latency is less critical
- System is operated and maintained by a single engineer ([C-3](/docs/requirements.md#c-3-team-size))

## Decision

Adopt an explicit **failure handling and degradation strategy** based on the
following principles:

1. **Correctness over availability for write operations**
2. **Availability over freshness for configuration**
3. **Fail fast and visibly when core dependencies are unavailable**
4. **Degrade functionality rather than allowing undefined behavior**

Failure handling behavior is **path-specific** and **dependency-specific**.

## Core Principles

### 1. Fail Closed on Writes

Operations that mutate state (e.g. URL shortening) must not proceed if
correctness cannot be guaranteed.

This prevents:
- Abuse
- Inconsistent state
- Quota bypass

### 2. Prefer Availability for Reads, Within Safety Bounds

Redirect operations prioritize:
- Low latency
- Predictable behavior

However, redirects must never return incorrect mappings.

### 3. Configuration Freshness Is Sacrificable

Temporary use of stale configuration is acceptable if it preserves:
- Availability
- Predictable behavior

### 4. Caching Is an Optimization, Not a Dependency

Cache failures must never cause:
- Request crashes
- Data corruption
- Undefined behavior

## Failure Handling by Component

### Redis Cloud Unavailable

Redis is the primary datastore for:
- URL resolution
- User quotas
- Link hit quotas

**Behavior:**

| Path       | Behavior                            |
|------------|-------------------------------------|
| Redirect   | Fail closed (reject request)        |
| Shorten    | Fail closed (reject request)        |
| Quotas     | Enforced only if Redis is reachable |

**Rationale:**
- Redirects cannot safely proceed without correct URL mapping
- Writes must not bypass quota enforcement

### AppConfig / Parameter Store / Secrets Unavailable

These services provide runtime configuration.

**Behavior:**
- Use cached configuration if available
- Accept temporary configuration staleness
- Do not block requests solely due to config unavailability

**Rationale:**
- Configuration changes are infrequent
- Availability is prioritized over immediate freshness

### Cache Failures or Stale Cache

Caching is used for performance optimization only.

**Behavior:**
- Cache miss → fetch from authoritative source
- Cache stale → tolerated within TTL bounds
- Cache corruption → cache may be flushed and rebuilt

**Rationale:**
- Cache correctness must never override authoritative sources
- TTLs bound the risk of stale data

### Cognito / Authorization Unavailable

Authentication applies only to protected endpoints.

**Behavior:**

| Endpoint Type | Behavior                   |
|---------------|----------------------------|
| Redirect      | Unaffected                 |
| Shorten       | Fail closed (unauthorized) |

**Rationale:**
- Public redirects must remain accessible
- Write operations must remain secure

### Lambda Cold Starts or Scaling Delays

**Behavior:**
- Requests may experience increased latency
- No retries or fallback logic at application level

**Rationale:**
- Cold starts are an accepted trade-off of serverless compute
- Complexity of custom mitigation outweighs benefit for this system

## Degradation Priorities

When forced to degrade, the system sacrifices capabilities in the following order:

1. **Freshness** (configuration, cache)
2. **Write availability** (shorten endpoint)
3. **Analytics and auxiliary behavior**
4. **Read availability** (redirects)

Security, correctness, and abuse prevention are **never sacrificed**.

## Alternatives Considered

### 1. Fail Open for Writes

**Pros**
- Higher availability

**Cons**
- Abuse risk
- Inconsistent state
- Quota bypass

**Rejected** due to correctness and security concerns.

### 2. Hard Dependency on Configuration Freshness

**Pros**
- Strong consistency

**Cons**
- Increased outage surface
- Cascading failures

**Rejected** in favor of resilience.

### 3. Complex Retry and Circuit-Breaker Logic

**Pros**
- More graceful recovery

**Cons**
- Significant complexity
- Harder reasoning
- Overkill for system scope

**Rejected** in favor of simplicity.

## Consequences

### Positive
- Predictable behavior under failure
- Clear operational expectations
- Strong correctness guarantees
- Reduced cascading failure risk

### Negative
- Reduced availability during certain failure modes
- Writes may be blocked even if partial functionality exists
- Some failures surface directly to users

## Impact

This decision directly influences:
- All request-path behavior
- Error handling semantics
- Cache TTL and invalidation strategy
- Operational expectations during outages
- Future scalability and resilience work

Any future architectural changes must preserve these failure-handling guarantees
unless explicitly revisited.

## Failure Matrix

This table summarizes how the system behaves when key dependencies fail.

| Dependency Failure | Affected Path | Behavior | Fail Mode | Rationale |
|-------------------|---------------|----------|-----------|-----------|
| Redis unavailable | Redirect (read) | Reject redirect request | Fail closed | Cannot safely resolve shortcode → incorrect redirect is worse than error |
| Redis unavailable | Shorten (write) | Reject shorten request | Fail closed | Prevent quota bypass and inconsistent state |
| Redis unavailable | User quota check | Reject write | Fail closed | Abuse prevention and correctness > availability |
| Redis unavailable | Link hit quota check | Reject redirect | Fail closed | Prevent unbounded traffic abuse |
| AppConfig unavailable | Redirect / Shorten | Use cached configuration | Fail open | Stale config acceptable to preserve availability |
| Parameter Store unavailable | Redirect / Shorten | Use cached values | Fail open | Configuration freshness < availability |
| Secrets Manager unavailable | Redirect / Shorten | Use cached secrets (if present) | Fail open | Short-lived staleness acceptable |
| Cache miss | Redirect / Shorten | Fetch from authoritative source | Fail open | Cache is an optimization, not a dependency |
| Cache stale | Redirect / Shorten | Continue within TTL bounds | Fail open | TTL bounds staleness risk |
| Cache corrupted | Redirect / Shorten | Flush cache and refetch | Fail open | Correctness restored via authoritative source |
| Cognito unavailable | Redirect (public) | Allow request | Fail open | Redirects are intentionally public |
| Cognito unavailable | Shorten (protected) | Reject request | Fail closed | Security > availability for writes |
| API Gateway authorizer failure | Shorten | Reject request | Fail closed | Authorization must not be bypassed |
| Lambda cold start | Redirect / Shorten | Increased latency | N/A | Accepted serverless trade-off |
| High concurrency | Quota enforcement | Best-effort enforcement | Partial fail closed | Redis atomicity guarantees correctness; minor contention tolerated |

The system intentionally fails closed for operations that affect correctness,
security, or abuse prevention, and fails open for operations where temporary
staleness or degraded behavior is acceptable.
