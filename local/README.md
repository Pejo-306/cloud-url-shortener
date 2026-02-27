# Local Docker Compose Stack

For local development we use a simple Compose stack made of:
- Redis (both for caching and backend data store)
- RedisInsight
- AppConfig Agent (serves AppConfig Configurations over a local endpoint via a simple GET request)
- Localstack (local SSM and Secrets Manager)

You can manage the local Compose stack via the [local Makefile](./Makefile).

## Prerequisites

- [Docker](https://www.docker.com/) v29.1+
- [Docker Compose](https://docs.docker.com/compose/) v2.40+

## Targets

Run from the `local/` directory:

| Target         | Description |
|----------------|-------------|
| `make up`      | Create and start the stack (detached) |
| `make down`    | Stop and remove the stack |
| `make destroy` | Stop and remove volumes & images |
| `make restart` | Restart the stack |
| `make help`    | Show help with example usage |

## Configurable Ports

Override ports when they conflict with other services on your machine:

| Variable               | Default | Description |
|------------------------|---------|-------------|
| `REDIS_PORT`           | 6379    | Redis database |
| `REDISINSIGHT_PORT`    | 5540    | Redis Insight web UI |
| `APPCONFIG_AGENT_PORT` | 2772    | AWS AppConfig Agent |
| `LOCALSTACK_EDGE_PORT` | 4566    | LocalStack main edge / AWS API |
| `LOCALSTACK_AUX_PORT`  | 4571    | LocalStack auxiliary gateway |

## Usage

```bash
# Start the stack
make up

# Start with custom Redis port
make up REDIS_PORT=7000

# Stop and remove the stack
make down

# Full teardown (volumes and images)
make destroy

# Restart
make restart
```
