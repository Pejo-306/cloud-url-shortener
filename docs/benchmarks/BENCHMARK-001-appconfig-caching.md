# AppConfig Caching Benchmark

## Goal

Measure the impact of [Phase 1 (lazy runtime caching)](/docs/decisions/ADR-007-caching-strategy.md) 
on AWS Lambda execution time for the `ShortenUrlFunction`.

## Baseline: No Cached AppConfig

### Setup
- AppConfig fetched on every invocation
- No local or external cache

### Results
- Duration: ~3190 ms
- Billed duration: ~3192 ms

(raw output below)

## Optimized: Cached AppConfig (ElastiCache)

### Setup
- AppConfig cached in ElastiCache
- Cache HIT on invocation

### Results
- Duration: ~2480 ms
- Billed duration: ~2485 ms

(raw output below)

## Comparison

| Metric          | No Cache | Cached   | Delta   |
|-----------------|----------|----------|---------|
| Duration        | ~3190 ms | ~2480 ms | ~700 ms |
| Billed duration | ~3192 ms | ~2485 ms | ~707 ms |

## Observations

- Caching AppConfig removes a significant portion of Lambda execution time
- Improvement is consistent and measurable

## Identified Risks

- Cache staleness if AppConfig updates are not propagated

## Follow-up Decisions

These findings motivated:
- TTL-based cache invalidation
- Event-driven cache warming ([ADR-007 Phase 2](/docs/decisions/ADR-007-caching-strategy.md))