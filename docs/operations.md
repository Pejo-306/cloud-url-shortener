# Operations Guide

This document describes how the `cloudshortener` system is **operated, deployed,
and maintained** in production environments.

## Deployment Model

### Sources of Truth

- Application code, infrastructure, and CI/CD configuration are versioned in GitHub
- Infrastructure is defined as code (CloudFormation / SAM / Terraform)
- No manual changes to cloud resources are expected outside of CI/CD workflows

### Deployment Flow (High-Level)

1. Code changes are pushed to GitHub and a pull request is raised
2. Our CI workflow:
   - Runs code quality checks
   - Runs unit tests
   - Packages build artifacts
3. On approved events (merged PR, created release branch, manual trigger), our CD workflow:
   - Unpackages build artifacts from CI
   - GitHub Actions authenticate to AWS via OIDC
   - Infrastructure and application are deployed using IaC tooling and bootstrap scripts in `staging` environment
   - Runs integration tests in `staging`

Deployments are **repeatable and idempotent**.

### Environments

The system supports multiple environments:
- `local`
- `dev`
- `staging`
- `prod`

Each environment:
- Has isolated configuration and secrets
- Uses separate cloud resources (except `local` which uses Docker containers)
- Is deployed independently

## Configuration Management

- Runtime configuration is stored in AWS AppConfig and cached in AWS ElastiCache
- Parameters and secrets are managed via AWS Parameter Store and AWS Secrets Manager
- Configuration changes do **NOT** require application redeployment
- Rollback is handled via AppConfig versioning and redeployment
- Temporary staleness is acceptable (see [ADR-007](/docs/decisions/ADR-007-caching-strategy.md), [ADR-011](/docs/decisions/ADR-011-failure-handling-and-degradation.md))

## Secrets and Credentials

- Secrets are rotated via Secrets Manager
- Secret access is scoped via IAM roles
- No long-lived AWS credentials are stored in GitHub
- CI/CD uses short-lived credentials via AWS OIDC trust
- Application code never embeds secrets

## Monitoring and Observability

We rely on the following sources for observability:
- Cloud provider-managed logs and metrics
- Lambda execution metrics (duration, errors, cold starts)
- API Gateway request metrics

## Failure Handling Expectations

Operational behavior during failures is defined in [ADR-011](/docs/decisions/ADR-011-failure-handling-and-degradation.md).

At a high level:
- Write operations may be rejected during partial outages
- Redirects prioritize correctness over availability
- Configuration staleness is tolerated within bounds
- Cache failures must not cascade

## Rollbacks and Recovery

### Application Rollback

Application rollbacks are performed via redeployment of a previous version.
Deployments are idempotent and scoped to a single environment.

### Configuration Rollback

AWS AppConfig supports versioned rollback without redeploying code.

### Data Recovery

Redis Cloud Pro backups provide hourly snapshots. Full dataset recovery is
possible with bounded data loss (see [ADR-003](/docs/decisions/ADR-003-data-durability.md)).

## Manual Intervention Guidelines

- Always check if AppConfig configuration is up to date and ElastiCache is not stale,
before taking any other actions
- Avoid direct modification of cloud resources
- If appropriate, trigger a redeploy to converge towards the desired state
- Document any manual actions taken

## Further Reading

- **[architecture.md](/docs/architecture.md)**: system architecture
- **[requirements.md](/docs/requirements.md)**: system constraints
- **[decisions/](/docs/decisions/)**: architectural and operational decisions
