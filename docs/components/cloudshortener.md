# `cloudshortener` - The backend

Serverless backend that shortens URLs (authenticated) and redirects shortcodes to targets (public). Backed by a primary data store. Enforces monthly user creation and link hits quotas.

## API

| Endpoint | Method | Auth | Description | API reference |
|----------|--------|------|-------------|---------------|
| `/v1/shorten` | POST | Yes | Create a shortened URL | [shorten_url.md](../api/shorten_url.md) |
| `/{shortcode}` | GET | No | Resolve a shortcode and redirect | [redirect_url.md](../api/redirect_url.md) |

## Data stores

| Name | Primary | Description | Schema |
|------|---------|-------------|--------|
| Redis Cloud Pro | Yes | Primary data store for shortcodes, targets, per-user and per-link monthly counters | [redis.md](../schemas/redis.md) |
| AWS ElastiCache | No | Application-level cache in Redis | [cache.md](../schemas/cache.md) |

## Further reading

- [Requirements](../requirements.md) — functional and non-functional constraints
- [Architecture](../architecture.md) — system design and major components
- [Decisions](../decisions/) — architectural decision records (ADRs)