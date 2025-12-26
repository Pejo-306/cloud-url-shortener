# ADR-014: Logging

## Status

Accepted

## Date

2025-12-26

## Context

We would like to add event logging to `cloudshortener` for better observability
and easier debugging.

Relevant documents:
- Cloud environment ([C-1](/docs/requirements.md#c-1-cloud-environment))
- The app is developed by a single developer - Pesho ([C-3](/docs/requirements.md#c-3-team-size))

## Decision

Use a simple environment-based logging level hierarchy. Implement logging via
Python's `logging` module and output logs in JSON format (AWS CloudWatch logs safe).

| Environment | Logging Level | Use Case                                                  |
|-------------|---------------|-----------------------------------------------------------|
| `local`     | `DEBUG`       | Detailed debug information to help with local development |
| `dev`       | `INFO`        | Regular informational logs                                |
| `staging`   | `INFO`        | Regular informational logs                                |
| `prod`      | `WARNING`     | Infrequent system warnings which should be addressed ASAP |

The selected log level is parsed to Lambda functions via an environment variable 
`LOG_LEVEL`, specified as a SAM parameter `LogLevel`. This approach is simple and
ensures logging is available at lambda initialization time.

Formatters and handlers are expected to be automatically configured **before**
the respective `lambda_handler` runs, i.e. in the function's `__init__.py` file.

## Alternatives Considered

### 1. No logging

**Pros**
- No implementation needed

**Cons**
- Makes it exponentially harder to debug the application as it's complexity grows

**Rejected** due to lack of observability concerns.

### 2. Storing log levels in AppConfig

**Pros**
- Configuration is stored in one source of truth - AppConfig

**Cons**
- More complex handling in code
- Not available at lambda initialization
- If AppConfig loading fails, we get no logs

**Rejected** due to introducing needless complexity for a quality-of-life improvement
like logging.

## Consequences

### Positive
- Easier to trace the root cause of application bugs

### Negative
- Introduces some additional implementation complexity
