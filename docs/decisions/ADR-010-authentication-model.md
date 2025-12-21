# ADR-010: Authentication and Authorization Model

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system exposes two categories of HTTP endpoints:

- **Public endpoints** (URL redirection)
- **Protected endpoints** (URL shortening)

The system must:
- Authenticate users creating short URLs
- Allow anonymous access to short URL redirects
- Scale authentication independently of application compute
- Minimize custom security logic in application code

Relevant requirements and constraints:
- Redirect endpoint is publicly accessible ([FR-2](/docs/requirements.md#fr-2-url-redirection))
- Shortening endpoint requires authentication ([FR-3](/docs/requirements.md#fr-3-authentication))
- Prefer fully managed services ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Minimize operational and security complexity ([C-3](/docs/requirements.md#c-3-team-size))
- Serverless compute model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Cloud provider is AWS ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md))

Implementing custom authentication logic would introduce:
- Security risks
- Token validation complexity
- Ongoing maintenance burden
- High blast radius for authentication bugs

## Decision

Use **Amazon Cognito** as the system’s **managed authentication provider**, and
enforce authorization at the **API Gateway level** using Cognito authorizers.

Specifically:
- Cognito manages user identities, credentials, and tokens
- API Gateway uses Cognito authorizers to protect selected endpoints
- Lambda functions assume requests are already authenticated where required

## Rationale

### Why Amazon Cognito

Amazon Cognito provides:
- Fully managed user pools
- Secure credential storage
- Standards-based authentication (OAuth 2.0 / OIDC)
- Token issuance and validation
- Seamless integration with API Gateway

Using Cognito allows the system to:
- Offload authentication complexity
- Avoid handling passwords or credentials directly
- Rely on a battle-tested identity service
- Scale authentication independently of application logic

### Authentication vs Authorization Boundary

The system clearly separates concerns:

- **Authentication**: Performed by Cognito (who the user is)
- **Authorization**: Enforced by API Gateway (what the user can access)

Lambda functions do **not** implement authentication logic themselves.

### API Gateway Authorizers

Authorization is enforced by attaching Cognito authorizers to specific API routes.

- Protected endpoints (e.g. URL shortening) require a valid Cognito-issued token
- Public endpoints (e.g. redirects) explicitly disable authorization

This ensures:
- Unauthorized requests never reach Lambda functions
- Reduced complexity in application code
- Consistent enforcement across all protected endpoints

### Identity Propagation

For authorized requests:
- API Gateway validates the token
- User identity claims are injected into the request context
- Lambda functions consume identity information as needed (e.g. user ID)

This enables:
- Per-user quota enforcement ([ADR-008](/docs/decisions/ADR-008-user-quota-enforcement.md))
- Auditable user actions
- Clear request attribution

## Alternatives Considered

### 1. Custom Authentication Implementation

**Pros**
- Full control over authentication logic
- Custom token formats

**Cons**
- High security risk
- Complex implementation
- Ongoing maintenance burden
- Easy to get wrong

**Rejected** due to unacceptable security and operational risk.

### 2. Lambda-Level Authentication

**Pros**
- Flexible per-function logic

**Cons**
- Authentication logic duplicated across functions
- Higher latency
- Inconsistent enforcement
- Harder to reason about security boundaries

**Rejected** in favor of centralized authorization at ingress.

### 3. Third-Party Identity Providers

**Pros**
- Feature-rich identity management
- Advanced integrations

**Cons**
- Additional dependencies
- Increased cost
- Less seamless integration with AWS infrastructure

**Rejected** in favor of native AWS integration and simplicity.

## Failure Considerations

- Cognito unavailability prevents access to protected endpoints
- Public redirect endpoints remain unaffected
- Authorization failures occur before Lambda execution

The system prioritizes **security over availability** for write operations.

## Consequences

### Positive
- No custom authentication code
- Strong security posture by default
- Centralized authorization enforcement
- Reduced attack surface
- Clear separation of concerns

### Negative
- Vendor lock-in to AWS identity services
- Limited flexibility compared to fully custom auth
- Dependency on Cognito availability for protected endpoints

## Impact

This decision directly influences:
- Security architecture and trust boundaries
- API Gateway configuration
- Lambda request handling assumptions
- Quota enforcement mechanisms
- Failure and degradation behavior

Future changes to authentication requirements or identity providers would require
revisiting ingress configuration and token handling.
