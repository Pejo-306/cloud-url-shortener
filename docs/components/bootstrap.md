# Component: `bootstrap` - Initialize the Backend

## Responsibility

Initializes AWS services, roles, parameters, and secrets required by runtime components.

This component prepares prerequisite infrastructure and configuration that is not managed by the main application stack but is required for deployment, CI/CD, and runtime operation.

## What Bootstrap Does

The `bootstrap` component consists of a collection of scripts that perform one-time 
or infrequent initialization tasks, including:

- Seeding AWS Systems Manager (SSM) Parameter Store values
- Seeding AWS Secrets Manager secrets
- Creating an OIDC-based IAM setup to allow GitHub Actions to run CI/CD workflows
- Creating and managing supporting CloudFormation stacks used for bootstrapping purposes

These scripts are currently executed manually from a local environment.  
In the future, the bootstrapping flow may be orchestrated via CI/CD pipelines or other automation.

**NOTE:** what this component does is subject to ever-evolve as the infrastructure
gets more complicated.

## Execution Model

- Bootstrap scripts are run **manually from the command line**
- Scripts are executed locally by an operator
- Idempotency and safety guarantees are **script-specific**
- Some scripts are safe to re-run; others intentionally overwrite values or fail if re-applied

There is no single “bootstrap command”; each script is run explicitly and intentionally.

## Target Environments

- Bootstrap scripts support **all application environments**
  - `local`
  - `dev`
  - `staging`
  - `prod`

Environment-specific behavior is controlled by script inputs and configuration.

## Inputs

- Inputs vary per script
- Common inputs include:
  - CLI flags
  - Environment variables
- A shared, required CLI flag across scripts:
  - `--aws-profile` — specifies the AWS CLI profile used for execution

Scripts are expected to be run with explicit operator intent and configuration.

## Outputs and Side Effects

Bootstrap scripts may create or mutate the following AWS resources:

- IAM roles
- IAM OIDC federators
- CloudFormation stacks (bootstrap-only)
- SSM Parameter Store values
- AWS Secrets Manager secret values

Bootstrap does **NOT** provision or manage the main backend application stack.

## Idempotency Guarantees

Idempotency is handled on a **per-script basis**:

- OIDC-related scripts:
  - Used to create or tear down the OIDC CloudFormation stack
  - Safe to re-run in the sense that:
    - Creating an existing stack fails cleanly
    - Stack rollback is handled by CloudFormation
- Parameter and secret seeding scripts:
  - Typically overwrite existing values
  - Re-running updates state rather than failing

Operators are expected to understand the behavior of each script before execution.

## Security Model

- Bootstrap scripts require elevated AWS permissions, including:
  - IAM role and policy management
  - CloudFormation stack creation
  - SSM Parameter Store writes
  - Secrets Manager writes
- Scripts may handle sensitive values (e.g. credentials, secrets)
- Sensitive data is written directly to AWS-managed services
- No guarantees are made that secrets never appear in process memory or local execution context
- Operators are responsible for:
  - Running scripts from secure environments
  - Using appropriate AWS profiles and credentials

Bootstrap is intended for trusted operators only.

## Failure Behavior

- Partial failure is possible:
  - Some parameters or secrets may be created or updated while others fail
- There is no global rollback mechanism across scripts
- For CloudFormation-managed resources:
  - Stack creation failures trigger automatic rollback
  - No partial stack state is left behind

After a failure, manual inspection and remediation may be required before retrying.

## Relationship to Other Components

- `bootstrap` is required **after deploying the main backend stack**
- Runtime components (e.g. `cloudshortener`) depend on bootstrap outputs for:
  - Configuration values
  - Secrets
  - CI/CD access

Bootstrap prepares the environment but does not deploy application code.

## Non-Goals

This component explicitly does **NOT**:
- Provision or manage the main backend application stack
- Deploy Lambda functions or APIs
- Manage networking or VPC configuration
- Act as a general-purpose infrastructure management tool

Bootstrap is intentionally narrow in scope and operationally explicit.