# `cloudshortener`: Cloud-based URL Shortener

URL shortening service using AWS Lambda Functions as compute and Redis Cloud as a backend database.

## Table of Contents

- [Background](#background)
- [System documentation](#system-documentation)
- [Local deployment](#local-deployment)
- [Cloud deployment](#cloud-deployment)
- [License](#license)

## Background

Before taking a position as a Software Engineer @ Redis, I wanted to practice system's design.

That's why I designed a cloud URL shortening service MVP in 3 weeks with 2 lambdas, a free Redis Cloud database and a barebones frontend.

The project has is evolving into a complex system. I am continuously developing this project to improve my skills.

## System documentation

For the original design narrative (requirements, capacity estimates, API, Redis key
schema, diagram, and deep dives), see **[docs/system-design.md](docs/system-design.md)**.

For formal requirements, high-level architecture, ADRs, and how to read the docs,
start at **[docs/README.md](docs/README.md)**.

## Local deployment

This project uses SAM and Docker to run AWS Lambda Functions in containers. A
[docker compose](local/compose.yaml) stack provides Redis, [Redis Insight](https://redis.io/insight/),
Localstack (parameters and secrets locally), and the AWS AppConfig Agent.

**NOTE**: Localstack is used for hybrid deployment (having AWS AppConfig in cloud, AWS lambda in local containers).

All commands assume you run from the **repository root**. Use the root [Makefile](Makefile) (`make help` for targets).

### Prerequisites

- [Python](https://www.python.org/) 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) (for frontend)
- [Docker](https://www.docker.com/) v 29.1+ and [Docker Compose](https://docs.docker.com/compose/) v2.40+
- [SAM](https://aws.amazon.com/serverless/sam/)

### Setup

1. Install dependencies: `make install`
2. Start Docker Compose: `make up`
3. Build backend, frontend, and infra: `make build`
4. Start the local SAM API (backend) and Vite dev server (frontend): `make dev`

Then:

- `POST` [localhost:3000/v1/shorten](http://localhost:3000/v1/shorten)
- `GET` [localhost:3000/{shortcode}](http://localhost:3000/Gh71TC0)

Sample events live under [events/](events/).

### Invoke functions directly

Invoke `ShortenUrlFunction`:

```bash
make invoke FUNCTION=ShortenUrlFunction EVENT_FILE=events/shorten_url/event.json
```

Invoke `RedirectUrlFunction`:

```bash
make invoke FUNCTION=RedirectUrlFunction EVENT_FILE=events/redirect_url/event.json
```

### A NOTE on arm64 containers

What happens if you get some error related to unsupported `arm64` architecture?

In [infra/stacks/backend/template.yaml](infra/stacks/backend/template.yaml) you might notice that the Lambda runtimes are
in `arm64` containers. It's because I'm developing on a Mac which is why native
`x86_64` didn't work for me well.

If you are developing on `x86_64` architecture (e.g. a Linux distribution), you
can switch out the architecture inside [infra/stacks/backend/template.yaml](infra/stacks/backend/template.yaml):

```yaml
Globals:
  Function:
    Timeout: 30
    Tracing: Active
    LoggingConfig:
      LogFormat: JSON
    Runtime: python3.13
    Architectures:
      - x86_64  # <-- switch this from `arm64` to `x86_64`
```

## Cloud deployment

AWS CloudFormation manages cloud resources.

All commands assume you run from the repository root. Use the root
[Makefile](Makefile) (`make help` for targets).

### Prerequisites

- [AWS Free Tier account](https://aws.amazon.com/free/) (paid one also works)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [act](https://github.com/nektos/act) and/or [GitHub](https://github.com/) with [GitHub Actions](https://github.com/features/actions)

### Configuration (.vars and .secrets)

The root Makefile reads variables from the environment (and from the command line). To avoid exporting values in every shell session, keep **non-sensitive** settings in **`.vars`** and **secrets** in **`.secrets`** at the repo root. Both filenames are gitignored.

Use **POSIX-style `export` lines** so you can load them with the shell `source` builtin:

**`.vars`** (optional; defaults match the Makefile if omitted):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `cloudshortener` | Application / stack name prefix |
| `APP_ENV` | `dev` | Environment (`dev`, `staging`, `prod`, …) |
| `LOG_LEVEL` | `INFO` | Lambda log level |
| `AWS_REGION` | `eu-central-1` | AWS region |
| `AWS_PROFILE` | `personal-dev` | AWS CLI profile |
| `GENERATE_FRONTEND_CONFIG` | `false` | If `true`, post-deploy generates `frontend/config/<APP_ENV>/app.config.json` from stack outputs |
| `REDIS_PORT` | `6379` | Local Compose: Redis port |
| `REDISINSIGHT_PORT` | `5540` | Local Compose: Redis Insight port |
| `LOCALSTACK_EDGE_PORT` | `4566` | Local Compose: Localstack edge port |
| `LOCALSTACK_AUX_PORT` | `4571` | Local Compose: Localstack auxiliary port |
| `APPCONFIG_AGENT_PORT` | `2772` | Local Compose: AppConfig Agent port |

**`.secrets`** (required for `make deploy`):

| Variable | Description |
|----------|-------------|
| `ELASTICACHE_PASSWORD` | 32–128 printable ASCII characters, no spaces, no `/*`, `"`, `@`, with at least one uppercase letter and one digit. Example: `bP7f2Qk9LxN4Rz8TgH3mVw6YcJ5pK1sD`. |

Example **`.vars`**:

```bash
export APP_NAME=cloudshortener
export APP_ENV=dev
export AWS_REGION=eu-central-1
export AWS_PROFILE=personal-dev
export GENERATE_FRONTEND_CONFIG=false
```

Example **`.secrets`**:

```bash
export ELASTICACHE_PASSWORD='your-password-here'
```

Before running `make` targets that need these values, load the files into your shell (omit either file if you do not use it):

```bash
set -a
[ -f .vars ] && . ./.vars
[ -f .secrets ] && . ./.secrets
set +a
```

You can also pass any variable on the command line instead, e.g. `make deploy ELASTICACHE_PASSWORD='...' APP_ENV=staging`.

### Setup

1. Deploy OIDC stack (allows GitHub Actions and `act` to deploy to AWS):

```bash
make bootstrap
```

To use an existing OIDC provider:

```bash
make bootstrap EXISTING_OIDC_PROVIDER_ARN=arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com
```

Override `GITHUB_ORG` and `REPO_NAME` if needed (see `make -C infra/bootstrap help`).

2. Create dev environment configuration files by editing and renaming the files:
- [config/shorten_url/dev.example.yaml](config/shorten_url/dev.example.yaml) → `config/shorten_url/dev.yaml`
- [config/redirect_url/dev.example.yaml](config/redirect_url/dev.example.yaml) → `config/redirect_url/dev.yaml`

```bash
cp config/shorten_url/dev.example.yaml config/shorten_url/dev.yaml
cp config/redirect_url/dev.example.yaml config/redirect_url/dev.yaml
# Edit both files with your config values
```

**NOTE:** dev.yaml / staging.yaml / prod.yaml are in *.gitignore*, so your secrets won't be committed.

3. Run seeding scripts, deploy SAM stack, and upload frontend:

```bash
make deploy GENERATE_FRONTEND_CONFIG=true
```

### Access the app

The **`FrontendUrl`** is printed in the deploy output and is also available on the CloudFormation stack’s **Outputs** tab in the AWS Console.

### Destroy the stack

```bash
make destroy
```

Happy shortening!

## License

This project is distributed under the [MIT license](LICENSE).
