# `ci-cd` — GitHub Actions

Continuous integration and deployment run as automated workflows under [`.github/workflows/`](../../.github/workflows/). CI validates code and templates; CD builds or reuses artifacts and deploys the stack.

## Authentication

Workflows authenticate with **federated OIDC**. There are no long-lived cloud credentials stored in GitHub or another repository. The [bootstrap stack](/infra/bootstrap/) provisions the identity provider, a CI/CD deploy role, and an IaC execution role.

Both CI and CD workflows assume the deploy role during their execution. CD will adiitionally pass the execution role to CloudFormation (so it can mutate resources) when deploying to AWS.

## CI

- Runs on pull requests and on pushes to `main` / release branches
- Lints IaC templates
- Performs code quality checks
- Builds SAM application and uploads build artifacts for CD

## CD

- Runs on successful CI run on `main` / release branches
- Downloads CI build artifacts, rebuilds if missing
- Seeds parameters and secrets
- Deploys resources and application to cloud provider
- Compiles, uploads and distributes frontend application

## Environments

We store environment parameters and secrets inside **GitHub Actions environment**. Supported environments:

- `dev`
- `staging`
- `prod`
