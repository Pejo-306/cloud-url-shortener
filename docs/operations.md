# Operations Guide

This document describes how the `cloudshortener` system is **operated, deployed,
and maintained** in production environments.

It focuses on **operational intent and expectations**, not on architectural
decisions (covered by ADRs) or local development setup (covered elsewhere).

## Scope and Audience

This document is intended for:
- The system operator (currently a single engineer)
- Future maintainers or reviewers
- Anyone responsible for deploying or modifying the system

It assumes familiarity with AWS, serverless systems, and CI/CD workflows.

## Deployment Model

### Source of Truth

- Application code, infrastructure, and CI/CD configuration are versioned in GitHub
- Infrastructure is defined as code (CloudFormation / SAM)
- No manual changes to cloud resources are expected outside of CI/CD workflows

### Deployment Flow (High-Level)

1. Code changes are pushed to the GitHub repository
2. GitHub Actions workflows:
   - Run automated tests
   - Validate build artifacts
3. On approved events (e.g. release branch or manual trigger):
   - GitHub Actions authenticates to AWS via OIDC
   - Infrastructure and application are deployed using IaC tooling

Deployments are **repeatable and idempotent**.

### Environments

The system supports multiple environments:
- `local`
- `dev`
- `staging`
- `prod`

Each environment:
- Has isolated configuration and secrets
- Uses separate cloud resources
- Is deployed independently

## Configuration Management in Operations

- Runtime configuration is externalized via AWS AppConfig
- Parameters and secrets are managed via Parameter Store and Secrets Manager
- Configuration changes do **NOT** require application redeployment

Operational expectation:
- Configuration changes should be rolled out carefully
- Rollback is handled via AppConfig versioning
- Temporary staleness is acceptable (see ADR-007, ADR-011)

## Secrets and Credentials

- No long-lived AWS credentials are stored in GitHub
- CI/CD uses short-lived credentials via AWS OIDC trust
- Application code never embeds secrets

Operational rules:
- Secrets are rotated via Secrets Manager
- Secret access is scoped via IAM roles
- Secrets should never be logged or exposed in metrics

## Monitoring and Observability (Operational View)

The system relies primarily on:
- Cloud provider-managed logs and metrics
- Lambda execution metrics (duration, errors, cold starts)
- API Gateway request metrics

Operational focus:
- Redirect latency and error rates
- Shorten endpoint error rates
- Redis connectivity and availability
- CI/CD deployment success/failure

Detailed observability decisions are intentionally kept lightweight.

## Failure Handling Expectations

Operational behavior during failures is defined in:
- **ADR-011: Failure Handling and Degradation Strategy**

At a high level:
- Write operations may be rejected during partial outages
- Redirects prioritize correctness over availability
- Configuration staleness is tolerated within bounds
- Cache failures must not cascade

Operators should expect **predictable failure modes**, not silent corruption.

## Rollbacks and Recovery

### Application Rollback

- Application rollbacks are performed via redeployment of a previous version
- Serverless deployments allow fast rollback with minimal blast radius

### Configuration Rollback

- AppConfig supports versioned rollback without redeploying code
- Configuration rollback is preferred over code rollback when applicable

### Data Recovery

- Redis Cloud Pro backups provide hourly snapshots
- Full dataset recovery is possible with bounded data loss (see ADR-003)

## Manual Intervention Guidelines

Manual intervention should be avoided where possible.

If required:
- Prefer configuration changes over code changes
- Avoid direct modification of cloud resources
- Document any manual actions taken

Manual changes should be treated as **temporary** and reconciled back into IaC.

## Operational Trade-Offs

This system intentionally favors:
- Simplicity over exhaustive automation
- Managed services over custom tooling
- Predictable behavior over maximal availability

These trade-offs are acceptable given:
- Project scope
- Team size
- Learning-focused goals

## Relationship to Other Documents

- **architecture.md** — system structure
- **requirements.md** — system constraints
- **decisions/** — architectural and operational decisions
- **benchmarks/** — performance evidence

This document explains **how the system is run**, not **why it is designed this way**.