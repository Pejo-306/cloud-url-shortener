# Component: `cloudshortener` - The Backend

## Responsibility

Implements backend URL shortening and URL resolution.

This component exposes HTTP APIs for creating short URLs and resolving them to their original targets. It is responsible for request validation, rate limiting, persistence, expiration handling, and redirection logic.

## Public Entry Points

| Endpoint      | Method | Auth | Description |
|--------------|--------|------|-------------|
| `/v1/shorten` | POST   | Yes  | Create a shortened URL |
| `/{shortcode}` | GET    | No   | Resolve a shortcode and redirect |

These endpoints are the **only supported public interfaces** of this component.

## Authentication Model

- **POST `/v1/shorten`**
  - Authentication is required
  - Amazon Cognito is used to manage users
  - API Gateway enforces authentication using a Cognito Authorizer
  - The Lambda function assumes the request is authenticated and extracts the user ID from JWT claims

- **GET `/{shortcode}`**
  - Always public
  - No authentication or authorization is applied

## Data Storage

### Primary Data Store
- **Redis** is the primary data store for:
  - Shortcode → target URL mappings
  - Per-user link generation quotas
  - Per-link hit counters and expiration state

### Supporting Storage
- Amazon ElastiCache may be used to host Redis
- Amazon S3 is used to store backups of Redis Cloud

### Data Store Abstraction
- All persistence is accessed through DAO interfaces
- The component is intentionally designed to support alternative backends in the future (e.g. DynamoDB, Cassandra, SQL databases)
- This enables benchmarking and comparison of different data store implementations without changing Lambda handlers

## Runtime Configuration

- AWS AppConfig stores Redis connection parameters and secrets
- Redis configuration values are sourced from:
  - AWS Systems Manager Parameter Store (host, port, db)
  - AWS Secrets Manager (username, password)
- Environment variables provide:
  - Application metadata (e.g. environment, application name)
  - Pointers to configuration sources

Runtime configuration is expected to be available for request handling.

## Rate Limiting and Expiration

### User-Level Rate Limiting
- Each authenticated user has a **monthly link generation quota**
- Exceeding the quota results in a `429 Too Many Requests` response
- Quota state is persisted in Redis

### Link-Level Rate Limiting
- Each shortened link has a **monthly hit quota**
- Each successful redirect decrements the remaining hit count
- When the quota is exceeded:
  - Requests return `429 Too Many Requests`
  - A `Retry-After` header indicates when the quota resets (beginning of next month)

### Expiration
- Links may expire based on configured policies
- Expired links are treated as unavailable and are not redirected

## Non-Goals

This component explicitly does **not** handle:
- Frontend UI or client-side logic
- Bootstrapping or provisioning AWS infrastructure
- Custom aliases
- Custom domains
- Admin or management APIs

These concerns are intentionally out of scope.

## Stability Guarantees

### Stable Contracts
- Public HTTP endpoints and methods
- Authentication requirements per endpoint
- HTTP status codes and error semantics
- Redirect behavior (`302 Location`)

### Not Guaranteed Stable
- Internal module and package structure
- DAO implementations
- Redis schema, key layout, or counters
- AppConfig configuration structure

Consumers must rely only on documented HTTP interfaces.

## Operational Constraints

- Implemented as AWS Lambda functions
- Optimized for short execution times
- Assumes low-latency access to Redis
- Availability depends on:
  - Redis availability
  - AppConfig availability
- Cold starts are expected but acceptable
- No guarantees are made regarding:
  - Exactly-once execution
  - Request ordering
  - Cross-request consistency beyond Redis guarantees

## Error Model

### HTTP Status Codes

| Status | Meaning |
|-------:|--------|
| 200 | Successful URL shortening |
| 302 | Successful redirect |
| 400 | Invalid request or missing parameters |
| 401 | Missing or invalid authentication |
| 429 | Rate limit exceeded (user or link level) |
| 500 | Internal server error |

### Error Codes

Error responses may include an `errorCode` field for machine-readable classification.

#### Common Error Codes

| Error Code | Description |
|-----------|------------|
| `MISSING_USER_ID` | Missing Cognito user identifier |
| `INVALID_JSON` | Malformed JSON request body |
| `MISSING_TARGET_URL` | Required `target_url` field missing |
| `LINK_QUOTA_EXCEEDED` | Monthly quota exceeded (user or link) |
| `MISSING_SHORTCODE` | Missing shortcode path parameter |
| `SHORT_URL_NOT_FOUND` | Shortcode does not exist |

- Error codes are **not guaranteed stable**
- Clients should primarily rely on HTTP status codes

## Future Extensions (Planned)

The following capabilities are planned and intentionally supported by the design:
- Analytics (e.g. per-link usage metrics)
- Swappable backend data store implementations for benchmarking and evaluation

All other extensions remain explicitly out of scope.