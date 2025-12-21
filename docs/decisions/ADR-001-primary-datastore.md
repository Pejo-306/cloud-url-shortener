# ADR-001: Primary Datastore for `cloudshortener`

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system must resolve short URLs with **low latency** and
**high throughput** under a **read-heavy workload**.

Relevant requirements:
- Minimal redirect latency ([NFR-1](/docs/requirements.md#nfr-1-performance))
- System supports a ~100:1 read-to-write ratio ([NFR-2](/docs/requirements.md#nfr-2-scalability))
- Up to 100 million daily active users ([NFR-2](/docs/requirements.md#nfr-2-scalability))
- Data retention up to 1 year ([NFR-4](/docs/requirements.md#nfr-4-data-retention))
- Fully managed services are preferred ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Wanted to use Redis so I gain experience with it

The primary access pattern is:
- Lookup by shortcode
- Simple key -> value retrieval
- Minimal query complexity and latency

The datastore sits on the **critical request path** for redirects and therefore
has a direct impact on user-perceived latency.

## Decision

Use a **centralized, in-memory key-value datastore (Redis)** to store shortcode-to-URL
mappings and resolutions.

All redirect requests read from this datastore. Write operations persist new shortcode
mappings to the same store.

If later needed, Redis Cloud datastore can be upscaled to multi-region active-active
deployment.

## Alternatives Considered

### 1. Relational Database

**Pros**
- Strong consistency
- Mature tooling
- Ubiquotous familiarity

**Cons**
- Higher read latency under extreme load
- Hard to scale horizontally
- Overkill for simple key-value access (no hard benefits of structured data for our system)

**Rejected** due to performance and scalability concerns

### 2. Distributed NoSQL Database (DynamoDB)

**Pros**
- Easy to scale horizontally
- Cheaper compared to in-memory key-value store
- Strong data durability
- Managed offerings available by AWS

**Cons**
- Higher latency compared to in-memory stores
- I don't get to use Redis for this project

**Rejected** in favor of using Redis.

## Consequences

### Positive
- Very low read latency for redirect operations
- Simple data model aligned with access patterns
- Built-in support for TTL-based retention and counters
- Minimal query complexity

### Negative
- In-memory storage is more expensive compared to disk/SSD-based storage
- Requires careful capacity planning to avoid eviction issues
- Risk of losing data (addressed in [ADR-003](/docs/decisions/ADR-003-data-durability.md))

## Impact

This decision directly impacts and informs:
- Choice of cloud provider ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md))
- Shortcode generation strategy ([ADR-004](/docs/decisions/ADR-004-shortcode-generation.md))
- TTL-based data retention
- Cache layering ([ADR-007](/docs/decisions/ADR-007-caching-strategy.md))
- Failure handling and degradation strategies

These concerns are addressed in subsequent ADRs.
