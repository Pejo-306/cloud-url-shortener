# Component: `ci-cd` – Continuous Integration & Deployment

## Responsibility

Defines and executes the continuous integration and continuous deployment workflows for the `cloudshortener` system.

This component is responsible for validating code changes, building deployment artifacts, and deploying the infrastructure and application to AWS in a controlled, environment-aware manner.

## Scope of Ownership

The CI/CD component **owns and manages**:

- Automated testing and coverage enforcement
- Build validation of the SAM application
- Deployment of the infrastructure and application stack
- Environment-specific deployments using GitHub Actions
- AWS authentication via OIDC (GitHub → AWS)

CI/CD does **NOT** provision AWS trust relationships or bootstrap IAM configuration; those are handled by the [bootstrap](/docs/components/bootstrap.md) component.

## Authentication Model (OIDC)

- GitHub Actions authenticate to AWS using **OIDC**
- No long-lived AWS credentials are stored in GitHub
- Trust is established via:
  - An IAM OIDC identity provider
  - One or more IAM roles assumable by GitHub workflows
- OIDC infrastructure is created and managed by [bootstrap](/docs/components/bootstrap.md)

CI/CD workflows assume a role with permissions scoped to deployment and validation tasks only.

## Workflow Overview

### 1. Continuous Integration (CI)

Triggered on:
- Pull requests to `main`
- Pushes to `main` and `release-*` branches

Responsibilities:
- Install dependencies
- Run unit tests
- Enforce test coverage threshold
- Validate SAM templates

Key properties:
- Python version is explicitly pinned
- Coverage threshold is enforced
- CI must pass before deployment can proceed

CI failures block merges and deployments.

### 2. Build Validation

Triggered on:
- Pushes to `main`
- Pushes to `release-*` branches

Responsibilities:
- Build the SAM application using container-based builds
- Validate that deployment artifacts can be produced
- Validate CloudFormation templates

Build artifacts are generated but not automatically deployed.

### 3. Deployment (CD)

Triggered via:
- Manual workflow dispatch
- Creation of release branches (`release-*`)

Responsibilities:
- Deploy the SAM stack to the selected environment
- Use environment-specific parameters and variables
- Deploy infrastructure and application code together

Deployment properties:
- One stack per environment: `{AppName}-{AppEnv}`
- Change sets are applied without interactive confirmation
- Deployment is gated on passing CI

## Environment Model

- CI/CD supports multiple environments:
  - `dev`
  - `staging`
  - `prod`
- Environment selection controls:
  - Stack name
  - AWS region
  - Parameter values
  - IAM role assumed via OIDC

Environment promotion is handled externally by branch and workflow controls, not automatically.

## Inputs

CI/CD workflows consume:

- Repository code
- GitHub Actions inputs (e.g. target environment)
- GitHub environment variables
- GitHub secrets (OIDC role ARNs only)

No static AWS credentials are used.

## Outputs and Side Effects

CI/CD workflows may:

- Deploy or update the SAM infrastructure stack
- Upload build artifacts for inspection
- Update CloudFormation-managed resources

CI/CD does **not**:
- Seed secrets or parameters
- Create IAM trust relationships
- Modify bootstrap-managed resources

## Failure Behavior

- CI failures:
  - Block deployment
  - Block merges (if enforced via branch protection)
- Deployment failures:
  - Leave CloudFormation stacks in a failed or rolled-back state
  - Require operator inspection and remediation
- Partial deployments are possible depending on CloudFormation behavior

CI/CD does not perform cross-environment rollback or promotion.

## Security Model

- AWS access is short-lived and scoped per workflow
- IAM permissions are limited to:
  - Stack deployment
  - Resource validation
- Secrets are not logged or persisted
- CI/CD is trusted to deploy but not to bootstrap or manage credentials

## Relationship to Other Components

- Depends on [bootstrap](/docs/components/bootstrap.md) for:
  - OIDC trust configuration
  - IAM roles
- Deploys and updates the [infrastructure](/docs/components/infrastructure.md) component
- Indirectly deploys runtime components (e.g. `cloudshortener`) via infrastructure

CI/CD orchestrates deployment but does not own runtime behavior.

## Non-Goals

This component explicitly does **NOT**:
- Provision AWS infrastructure prerequisites
- Manage secrets or parameter values
- Perform data migrations
- Automatically promote changes between environments
- Act as a general-purpose automation system

CI/CD is intentionally narrow in scope and deployment-focused.
