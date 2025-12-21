# ADR-012: Continuous Integration and Deployment Strategy

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system is developed and maintained in a GitHub repository and
is deployed to AWS infrastructure.

The project requires:
- Automated validation of code changes
- Repeatable, deterministic builds
- Safe and auditable deployments to AWS
- Minimal operational overhead for a single-engineer project ([C-3](/docs/requirements.md#c-3-team-size))
- Tight integration with existing tooling and workflows

Relevant requirements and constraints:
- Infrastructure is defined as code ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md))
- Serverless deployment model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Secure authentication between CI/CD system and AWS
- No long-lived cloud credentials stored in source control

Given that the source code already resides in GitHub, introducing a separate CI/CD
platform would increase complexity without providing clear benefits.

## Decision

Use **GitHub Actions** as the primary platform for **continuous integration and
continuous deployment (CI/CD)**.

Authenticate GitHub Actions to AWS using an **OIDC-based trust relationship**,
eliminating the need for long-lived AWS credentials.

## Rationale

### Why GitHub Actions

GitHub Actions provides:
- Native integration with GitHub repositories
- Event-driven workflows (pull requests, pushes, releases)
- First-class support for CI and CD pipelines
- Simple workflow-as-code configuration
- No additional infrastructure to manage

Using GitHub Actions allows:
- CI/CD configuration to live alongside application code
- Reduced cognitive and operational overhead
- Faster iteration and simpler debugging of pipeline behavior

### Integration with AWS

Deployments target AWS-managed infrastructure and services.

GitHub Actions integrates cleanly with AWS via:
- Official AWS-provided actions
- Standard tooling (AWS CLI, SAM, CloudFormation)
- Native support for OpenID Connect (OIDC)

This enables secure, short-lived authentication for deployment workflows.

### Why OIDC for AWS Authentication

Instead of static access keys, the system uses an **OIDC trust relationship**
between GitHub and AWS.

This approach:
- Eliminates long-lived AWS credentials
- Reduces risk of credential leakage
- Provides fine-grained, auditable access control
- Aligns with AWS security best practices

An AWS-side **OIDC bootstrap stack** establishes:
- A trusted identity provider for GitHub Actions
- IAM roles scoped specifically for deployment actions
- Least-privilege permissions for CI/CD workflows

## CI/CD Workflow Overview

At a high level, the CI/CD process includes:
- Automated unit tests on pull requests
- Build and validation steps on merges
- Controlled deployments via branch or release events
- Environment-specific deployments (dev, staging, prod)

All workflows are defined declaratively and versioned in the repository.

## Alternatives Considered

### 1. Dedicated CI/CD Platforms (e.g. Jenkins, CircleCI)

**Pros**
- Feature-rich pipelines
- Mature ecosystems

**Cons**
- Additional setup and maintenance
- External system to manage and secure
- No clear benefit over GitHub Actions for this project

**Rejected** due to unnecessary complexity.

### 2. Static AWS Credentials in CI

**Pros**
- Simple initial setup

**Cons**
- High security risk
- Manual credential rotation
- Poor auditability

**Rejected** due to security concerns.

### 3. Manual Deployment

**Pros**
- Full control

**Cons**
- Error-prone
- Not repeatable
- Does not scale beyond trivial systems

**Rejected** in favor of automated pipelines.

## Failure Considerations

- CI failures block merges or deployments
- Authentication failures prevent deployment but do not affect runtime systems
- Deployment workflows fail safely without partial infrastructure changes

CI/CD failures are isolated from production traffic and do not impact system
availability.

## Consequences

### Positive
- Secure, automated deployments
- No long-lived cloud credentials
- CI/CD configuration versioned with code
- Minimal operational overhead
- Clear audit trail for changes and deployments

### Negative
- Vendor lock-in to GitHub ecosystem
- Limited flexibility compared to fully custom pipelines
- CI availability depends on GitHub uptime

## Impact

This decision directly influences:
- Development workflow and velocity
- Deployment safety and repeatability
- Security posture of the build and release process
- Infrastructure access control
- Operational confidence in releases

Future changes to repository hosting or cloud provider would require revisiting
CI/CD tooling and authentication mechanisms.