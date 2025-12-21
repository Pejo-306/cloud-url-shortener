# ADR-005: Serverless Compute Model

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system requires compute to handle two primary workloads:

- A **latency-critical, read-heavy redirect path**
- A **less latency-sensitive, write-heavy shortening path**

Relevant requirements and constraints:
- Prefer fully managed and serverless services ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Support extreme horizontal scalability ([NFR-2](/docs/requirements.md#nfr-2-scalability))
- Minimize operational overhead for a single-engineer project ([C-3](/docs/requirements.md#c-3-team-size))
- Enable rapid iteration during a 3-week MVP ([C-2](/docs/requirements.md#c-2-time-constraints))
- Primary datastore (Redis Cloud) is externally managed ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))
- Cloud provider is AWS ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md))

The system does **not** require:
- Long-running background workers
- Stateful compute
- Custom autoscaling logic
- Fine-grained control over host infrastructure

## Decision

Use a **serverless compute model**, implemented using **AWS Lambda Functions**, for
all backend compute in the system.

Each major responsibility is implemented as an independent, stateless function:
- Redirect handling (read path)
- URL shortening (write path)

All persistent state is externalized to managed services.

## Rationale

### Why Serverless Compute

Serverless compute provides:
- Automatic horizontal scaling
- Built-in fault tolerance
- No infrastructure provisioning or capacity planning
- Simple pay-per-use cost model
- Tight integration with other managed cloud services

This aligns directly with the project’s goals of:
- Fast MVP delivery
- Minimal operational burden
- Focus on system design rather than infrastructure management

### Statelessness as a First-Class Constraint

All Lambda functions are designed to be **fully stateless**:
- No local persistence
- No reliance on execution reuse
- No in-memory assumptions across invocations

This ensures:
- Safe horizontal scaling
- Simple failure semantics
- Predictable behavior under concurrency

Persistent state is handled exclusively by Redis Cloud and other managed services.

### Cold Start Considerations

Cold starts are acknowledged as an inherent trade-off of serverless compute.

Mitigations:
- Redirect logic is intentionally minimal
- Dependencies are kept lightweight
- Configuration is cached where possible (see caching ADR)

The system accepts occasional cold-start latency as an acceptable trade-off for
operational simplicity and scalability.

### Read vs Write Path Characteristics

The serverless model allows natural differentiation between:
- **Redirect path**: optimized for speed and simplicity
- **Shorten path**: optimized for correctness and quota enforcement

Each path scales independently based on demand without custom orchestration.

## Alternatives Considered

### 1. Container-Based Services (ECS / Kubernetes)

**Pros**
- Greater control over runtime environment
- Potentially lower latency for warm services

**Cons**
- Higher operational complexity
- Requires capacity planning and scaling policies
- Overkill for a single-engineer MVP

**Rejected** due to operational overhead and misalignment with project goals.

### 2. Virtual Machines (EC2)

**Pros**
- Full control over infrastructure
- Predictable performance

**Cons**
- Manual scaling and failover
- Ongoing maintenance burden
- Poor fit for bursty, read-heavy workloads

**Rejected** due to high operational cost and low agility.

## Time Complexity and Latency Impact

- Compute execution time is proportional only to request logic
- No blocking I/O beyond managed service calls
- Horizontal scaling occurs automatically under load

The serverless model does **not** introduce algorithmic complexity and does not
impact the critical redirect path beyond cold-start considerations.

## Consequences

### Positive
- Zero infrastructure management
- Automatic horizontal scaling
- Fault isolation per invocation
- Fast iteration and deployment
- Clear separation between compute and state

### Negative
- Cold-start latency under low traffic
- Vendor lock-in to cloud provider runtime
- Less control over execution environment

## Impact

This decision directly influences:
- Application structure (stateless design)
- Dependency management and packaging
- Observability and monitoring approach
- Cost model and scaling behavior
- Caching and configuration strategies

Future requirements such as background processing, long-running jobs, or
real-time streaming may require revisiting this decision.