# AWS SAM Infrastructure

Our AWS infrastructure is managed by CloudFormation and SAM in standalone component stacks. These stacks can be deployed separately or as nested stacks within the full application architecture. The orchestrator stack deploys the full application (Network, Cognito, AppConfig, Frontend, ElastiCache, Backend).

You can manage the infrastructure via the [infra Makefile](./Makefile).

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) v2
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) v1.x
- [Docker](https://www.docker.com/) (for `sam build --use-container`)

## Targets

Run from the `infra/` directory:

| Target         | Description |
|----------------|-------------|
| `make build`   | Build orchestrator template |
| `make deploy`  | Deploy entire stack (builds frontend, runs sync) |
| `make destroy` | Destroy entire stack |
| `make deploy-*` | Deploy a specific stack |
| `make build-*`  | Build a specific stack |
| `make destroy-*` | Destroy a specific stack |
| `make local-api` | sam local start-api |
| `make invoke FUNCTION=<name>` | sam local invoke |

For standalone stack deploy/build/destroy, refer to `make help`.

## Configurable Variables

Override when deploying via `make deploy APP_ENV=staging`:

| Variable    | Default        | Description                 |
|-------------|----------------|-----------------------------|
| `APP_NAME`  | cloudshortener | Application name            |
| `APP_ENV`   | dev            | Environment                 |
| `LOG_LEVEL` | INFO           | Logging level               |
| `AWS_REGION` | eu-central-1  | AWS region                  |
| `AWS_PROFILE` | personal-dev | AWS profile                 |
| `S3_BUCKET` | (managed)      | S3 bucket for SAM artifacts |

## Usage

**PREREQUISITES:** Ensure frontend and backend can be built successfully (`make build` in `frontend/` and `backend/`).

Deploy the full stack from `infra/`:

```bash
make deploy
```

After you're done using it, remember to clean up:

```bash
make destroy
```

For standalone stack deploy/build/destroy, refer to `make help`.
