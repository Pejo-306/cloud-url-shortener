# ADR-006: Configuration and Secrets Management

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system is deployed across multiple environments
(local, dev, staging, prod) and relies on several configuration values
that may change independently of code deployments.

Relevant requirements and constraints:
- Minimize operational overhead ([C-3](/docs/requirements.md#c-3-team-size))
- Prefer fully managed services ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Support rapid iteration without frequent redeployments ([C-2](/docs/requirements.md#c-2-time-constraints))
- Serverless, stateless compute model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Sensitive credentials must be protected
- Configuration must differ per environment

The system requires configuration for:
- Redis connection parameters
- Cache configuration
- Environment-specific feature toggles
- Credentials and secrets

Embedding configuration directly into deployment artifacts or code would:
- Require redeployment for simple configuration changes
- Increase blast radius of configuration errors
- Risk accidental leakage of secrets

## Decision

Use **AWS-managed configuration services** with a clear separation of concerns:

- **AWS AppConfig** for structured, versioned application configuration
- **AWS Systems Manager Parameter Store** for non-secret parameters
- **AWS Secrets Manager** for sensitive credentials and secrets

All runtime configuration is **externalized** and loaded dynamically by
serverless compute components.

## Rationale

### Separation of Configuration Types

Different classes of configuration have different operational needs:

| Configuration Type       | Characteristics                          | Service Used          |
|--------------------------|------------------------------------------|-----------------------|
| Application configuration| Versioned, structured, frequently read   | AWS AppConfig         |
| Non-secret parameters    | Simple values, infrequently rotated       | Parameter Store       |
| Secrets & credentials    | Sensitive, rotation-capable               | Secrets Manager       |

Separating these concerns improves clarity, security, and operational safety.

### Why AWS AppConfig

AWS AppConfig is used for **application-level configuration** because it provides:
- Versioned configuration deployments
- Environment scoping
- Safe rollout strategies
- Validation and rollback mechanisms
- No redeployment required for updates

This is particularly valuable in a serverless architecture, where redeploying
functions solely for configuration changes is undesirable.

### Why Parameter Store

Parameter Store is used for:
- Non-sensitive environment parameters
- Values that rarely change
- Configuration referenced by AppConfig

It provides:
- Simple key–value access
- IAM-based access control
- Low operational overhead

### Why Secrets Manager

Secrets Manager is used for:
- Database credentials
- Passwords and tokens
- Any sensitive configuration values

It provides:
- Encryption at rest and in transit
- Fine-grained IAM access control
- Support for rotation workflows
- Clear separation from non-secret configuration

### Runtime Configuration Loading

At runtime:
- Lambda functions retrieve configuration via AppConfig
- AppConfig references parameters and secrets indirectly
- Configuration is cached locally where appropriate (see caching ADR)

This ensures:
- Stateless compute remains lightweight
- Configuration can evolve independently of code
- Secrets are never hardcoded or logged

## Alternatives Considered

### 1. Configuration Embedded in Code or Environment Variables

**Pros**
- Simple to implement
- No external dependencies

**Cons**
- Requires redeployment for any change
- Poor secret handling
- High risk of configuration drift
- Difficult to manage across environments

**Rejected** due to operational and security risks.

### 2. Single Configuration Store for All Values

**Pros**
- Fewer services to manage
- Simpler mental model

**Cons**
- Conflates secrets with non-secrets
- Reduces clarity of responsibility
- Harder to enforce least-privilege access

**Rejected** in favor of explicit separation of concerns.

### 3. Custom Configuration Service

**Pros**
- Full control
- Tailored behavior

**Cons**
- Significant implementation effort
- High operational burden
- Reinvents managed solutions

**Rejected** as unnecessary complexity.

## Failure Considerations

- Configuration services are treated as **external dependencies**
- Cached configuration may become stale temporarily
- The system prioritizes availability over immediate configuration freshness

Failure modes and mitigation strategies are addressed in the caching and
failure-handling ADRs.

## Consequences

### Positive
- Configuration changes without redeployment
- Clear separation between code, config, and secrets
- Improved security posture
- Reduced operational risk
- Environment-specific configuration handled cleanly

### Negative
- Increased number of managed services
- Additional runtime dependencies
- Requires careful cache invalidation strategy

## Impact

This decision directly influences:
- Application startup and request handling
- Caching strategy ([ADR-007](/docs/decisions/ADR-007-caching-strategy.md))
- Failure modes and resilience
- Operational workflows for configuration changes
- Security and access control model

Future changes to configuration complexity or scale may require revisiting
deployment strategies or caching policies.