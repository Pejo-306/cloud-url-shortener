# TTL caching tiers in seconds
# NOTE: refer to [ADR-013](/docs/decisions/ADR-013-caching-ttls.md) for more details.
HOT_TTL = 60 * 60  # 60 minutes * 60 seconds = 60 minutes
WARM_TTL = 24 * 60 * 60  # 24 hours * 60 minutes * 60 seconds = 24 hours
COOL_TTL = 7 * 24 * 60 * 60  # 7 days * 24 hours * 60 minutes * 60 seconds = 7 days