# OIDC stack and seeding scripts

OIDC bootstrap stack so GitHub Actions can deploy the application to AWS (GitHub OIDC provider, deploy role, CloudFormation exec role). Seeding scripts for provisioning config, secrets, and other bootstrapping actions.

You can manage the OIDC stack and bootstrapping scripts via the [infra/bootstrap Makefile](./Makefile).

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.13+
- [AWS CLI](https://aws.amazon.com/cli/) v2

## Targets

Run from the `infra/bootstrap/` directory:

| Target   | Description                    |
|----------|--------------------------------|
| `make oidc-up` | Deploy OIDC bootstrap stack |
| `make oidc-down` | Delete OIDC bootstrap stack |
| `make help` | Show seeding targets and help |

Seeding targets (see `make help` for current list).

## Configurable Variables

| Variable     | Default                  | Description               |
|--------------|--------------------------|---------------------------|
| `STACK_NAME` | cloudshortener-bootstrap | CloudFormation stack name |
| `APP_NAME`   | cloudshortener           | Application name          |
| `APP_ENV`    | dev                      | Environment               |
| `AWS_PROFILE` | personal-dev            | AWS profile               |
| `GITHUB_ORG` | Pejo-306                  | GitHub org for OIDC       |
| `REPO_NAME`  | cloud-url-shortener      | GitHub repo               |

## Usage

Deploy the OIDC stack with an existing OIDC provider:

```bash
make oidc-up EXISTING_OIDC_PROVIDER_ARN=arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
```

Reference `make help` for specific bootstrapping scripts.
