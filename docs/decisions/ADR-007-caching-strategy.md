# ADR-007: Caching Strategy

## Status

Accepted (Phase 1 implemented, Phase 2 planned)

## Date

2025-12-21

## Context

The `cloudshortener` system relies on external managed services that are accessed
at runtime, most notably:

- Application configuration delivered via **AWS AppConfig**
- Parameters and secrets referenced by configuration
- Stateless serverless compute ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))

The system includes:
- A **latency-critical redirect path**
- Stateless Lambda functions with ephemeral execution environments
- Configuration values that are read frequently but change infrequently

Fetching configuration and metadata from external services on every invocation
would:
- Increase request latency
- Increase cost
- Increase coupling to external service availability

At the same time, caching introduces risks related to:
- Stale configuration
- Inconsistent behavior across invocations
- Cache invalidation complexity

## Decision

Adopt a **two-phase caching strategy** that balances simplicity, safety, and
performance:

- **Phase 1 (Implemented)**: *Lazy, on-demand caching during Lambda execution*
- **Phase 2 (Planned)**: *Event-driven, proactive cache warming*

Caching is treated strictly as a **performance optimization**, never as a source
of truth.

## Phase 1: Lazy Runtime Caching (Implemented)

### Description

During Lambda execution:
- If a required value (e.g. application configuration) is **not cached**, it is
  fetched from the authoritative source and cached.
- If the value **is cached**, it is retrieved directly from the cache.

This pattern applies primarily to:
- Application configuration retrieved via AppConfig
- Derived configuration values computed from configuration data

### Cache Scope and Lifetime

- Cache is stored **in-memory within the Lambda execution environment**
- Cache is reused across warm invocations
- Cache is discarded automatically when the execution environment is recycled

No assumptions are made about cache persistence.

### Use of TTLs

Cached entries are associated with **time-based expiration (TTL)** values.

TTLs are used to:
- Bound the maximum staleness of cached values
- Force periodic refresh from authoritative sources
- Reduce risk from long-lived warm execution environments

Exact TTL values are **intentionally not fixed** at this stage and will be
defined in subsequent ADRs based on:
- Configuration change frequency
- Risk tolerance for stale values
- Observed production behavior

### Rationale

This approach:
- Requires no additional infrastructure
- Minimizes code complexity
- Works naturally with serverless execution semantics
- Provides immediate performance benefits

It represents the safest possible caching strategy for an MVP system.

## Phase 2: Event-Driven Cache Warming (Planned)

### Description

Introduce a **separate, dedicated Lambda function** responsible for proactively
warming caches.

This function will be triggered by events such as:
- Application configuration deployments
- Environment-level configuration changes

Upon trigger, the function:
- Fetches the latest configuration
- Updates the shared cache so that subsequent request Lambdas start with fresh
  values

### Goals

Phase 2 caching aims to:
- Reduce cache-miss latency on the first request after configuration changes
- Minimize exposure to stale configuration
- Decouple configuration freshness from request traffic patterns

This phase does **NOT** replace TTL-based expiration and does **NOT** eliminate
the need for lazy caching.

### Constraints

- Proactive cache warming must be **best-effort**
- Failure to warm cache must not affect request handling
- The authoritative source remains AppConfig and parameter stores

Phase 2 is an optimization layered on top of Phase 1, not a dependency.

## Alternatives Considered

### 1. No Caching

**Pros**
- Simplest model
- Always fresh configuration

**Cons**
- Higher latency
- Increased cost
- Increased dependency on external services

**Rejected** due to inefficiency and unnecessary coupling.

### 2. Aggressive or Permanent Caching Without TTLs

**Pros**
- Maximum performance
- Minimal external calls

**Cons**
- High risk of stale configuration
- Difficult recovery from misconfiguration
- Poor operational safety

**Rejected** due to unacceptable staleness risk.

### 3. Distributed Cache as Primary Configuration Source

**Pros**
- Shared cache across invocations
- Strong performance characteristics

**Cons**
- Introduces another critical dependency
- Requires explicit invalidation logic
- Overlaps with managed configuration services

**Rejected** in favor of simpler, incremental caching.

## Failure Considerations

- Cache misses fall back to authoritative sources
- Cache staleness is bounded by TTLs
- Cache warming failures do not impact request correctness
- Configuration availability is prioritized over freshness

The system is designed to **fail safe**, not fast.

## Consequences

### Positive
- Reduced latency on hot paths
- Lower cost from fewer external service calls
- Graceful degradation during partial outages
- Incremental complexity aligned with system maturity

### Negative
- Risk of temporary configuration staleness
- Additional cache management logic
- Requires observability around cache behavior

## Impact

This decision directly influences:
- Request latency characteristics
- Configuration freshness guarantees
- Failure modes under partial outages
- Observability and alerting needs
- Future operational optimizations

TTL tuning, cache scope expansion, and additional cache layers will be addressed
in future ADRs as the system evolves.

## Evidence

Empirical benchmarking shows that Phase 1 (lazy runtime caching) reduces AWS
Lambda execution time for the shorten URL path by approximately **700 ms** per
invocation when AppConfig is cached.

Detailed benchmark results, methodology, and raw outputs are documented in:
- [AppConfig Caching Benchmark](/docs/benchmarks/BENCHMARK-001-appconfig-caching.md)