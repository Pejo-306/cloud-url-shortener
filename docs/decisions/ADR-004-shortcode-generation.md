# ADR-004: Shortcode Generation Strategy

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Revision History

- 2025-12-25: Updated to use multiplicative permutation instead of simple addition for better sequential scrambling

## Context

The `cloudshortener` system must generate **short, URL-safe identifiers**
(shortcodes) that map to long URLs.

Relevant requirements and constraints:
- Each shortcode must map **1:1** to a long URL at any given time ([FR-1](/docs/requirements.md#fr-1-url-shortening))
- Shortcodes must be compact and URL-safe
- Generation must be fast and deterministic
- The system must support very large keyspaces ([NFR-2](/docs/requirements.md#nfr-2-scalability))
- Short URLs are retained for up to 1 year ([NFR-4](/docs/requirements.md#nfr-4-data-retention))
- The primary datastore is Redis ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))

Additionally:
- The system uses a **monotonically increasing counter** to uniquely identify links
- Shortcodes should not reveal internal sequencing or system state

## Decision

Use a **counter-based, deterministic shortening algorithm** with the following properties:

- A **globally unique numeric counter** is used as the source of uniqueness
- The counter value is **permuted using a multiplicative transformation** combined with a **secret salt** to obscure sequential patterns
- The resulting value is **encoded into a fixed-length Base62 string**
- Output length is fixed (7 characters) to ensure predictable URL size
- Old shortcodes expire, allowing safe reuse of the output space over time

The algorithm uses a **multiplicative permutation** (affine transformation) to ensure that sequential counters produce completely unrelated-looking shortcodes while maintaining a 1:1 bijective mapping. The algorithm is deterministic, fast, and collision-free within the system's operational assumptions.

## Rationale

### Why a Counter-Based Strategy

A counter provides:
- Guaranteed uniqueness at generation time
- O(1) lookup and write semantics
- Simplicity and predictability

Unlike random or probabilistic approaches, a counter eliminates the need for
collision retries or existence checks during generation.

### Why Multiplicative Permutation and Salting Are Applied

Using a raw counter directly would:
- Reveal internal system state
- Allow enumeration of URLs
- Create predictable shortcodes

A simple additive salt (counter + salt_hash) was initially used, but this approach had a limitation: sequential counters would produce shortcodes that were visually similar, with only minor differences (often just the last character). This could still reveal sequential patterns.

To better mitigate this, the counter is now:
- **Multiplied by a coprime factor** to create a multiplicative permutation
- **Combined with a secret salt** (additive component) via an affine transformation
- Passed through a fast, non-cryptographic hash (xxhash) for the salt
- Wrapped into a bounded numeric space

The affine transformation `(counter * mult + salt_hash) mod (BASE^length)` where `mult` is coprime with `BASE^length` ensures:
- **1:1 bijective mapping**: Each counter maps to exactly one permuted value
- **Complete scrambling**: Sequential counters produce completely different shortcodes
- **Deterministic output**: Same inputs always produce the same output

This preserves uniqueness while completely obscuring sequential patterns.

### Why Fixed-Length Base62 Encoding

Base62 encoding:
- Uses only URL-safe characters (`a–z`, `A–Z`, `0–9`)
- Maximizes the number of representable values per character
- Produces compact, human-friendly identifiers

With a length of 7 characters, the total addressable space is 
`62^7 ≈ 3.5 trillion possible shortcodes`.

This comfortably exceeds the system’s expected annual link volume.

## Collision Avoidance and 1:1 Mapping

### Collision Avoidance

Collisions are avoided by design:

- Each new URL is assigned a **unique counter value**
- The counter space is mapped deterministically to a large output space
- The output space is orders of magnitude larger than the active dataset

Although modulo wrapping technically introduces the *possibility* of collisions,
this is mitigated by:
- A limited retention period (1 year)
- A sufficiently large output space
- Low probability of overlapping active keys

In practice, the risk of collisions during the retention window is negligible.

### Ensuring 1:1 Mapping

- Each shortcode is generated once and persisted immediately
- Redis enforces uniqueness at the key level
- Shortcodes are not regenerated for existing URLs
- Expired URLs free their shortcode space for future reuse

At any point in time, each active shortcode maps to exactly one long URL.

## Algorithm Overview (Pseudocode)

The shortcode generation algorithm is based on a **monotonically increasing
counter**, combined with a **secret salt** via a **multiplicative permutation**,
and encoded into a fixed-length Base62 representation.

The algorithm can be described as follows:

```c++
INPUT:
counter        // globally unique integer
salt           // secret string
length         // fixed shortcode length (e.g. 7)
mult           // multiplicative factor (must be coprime with BASE^length)
alphabet       // Base62 character set [a–zA–Z0–9]

PROCESS:
modulo_space = BASE^length
hash_salt = HASH(salt) mod modulo_space
permuted = (counter * mult + hash_salt) mod modulo_space

shortcode = ""
for i from 0 to length - 1:
digit = (permuted / BASE^i) mod BASE
shortcode = alphabet[digit] + shortcode

if length(shortcode) < length:
pad shortcode with leading alphabet[0]

OUTPUT:
shortcode
```

### Properties

- **Deterministic**: same `(counter, salt, mult)` always produces the same shortcode
- **Fixed-length**: output length is constant
- **URL-safe**: Base62 alphabet only
- **Non-sequential**: sequential counters produce completely unrelated shortcodes
- **Bijective**: 1:1 mapping between counter space and output space (when `counter < BASE^length`)
- **O(1)** time complexity

The counter guarantees uniqueness at generation time, while the multiplicative permutation and encoding ensure compactness and complete opacity of sequential patterns.

### Multiplicative Factor Requirements

The multiplicative factor `mult` must be **coprime** with `BASE^length` (i.e., `gcd(mult, BASE^length) == 1`) to ensure the affine transformation is bijective. This guarantees that:
- Each counter value maps to a unique permuted value
- The mapping is reversible (though not needed in practice)
- No collisions occur within the counter space `[0, BASE^length)`

The default value `1315423911` is chosen to be coprime with `62^7` and provides good scrambling properties.

## Alternatives Considered

### 1. Random String Generation

**Pros**
- Simple to implement
- No counter management

**Cons**
- Requires collision detection and retries
- Unbounded generation time under high load
- Harder to reason about guarantees

**Rejected** due to probabilistic collisions and retry overhead.

### 2. UUIDs

**Pros**
- Practically collision-free
- Widely used

**Cons**
- Too long for URL shortcodes
- Poor user experience
- Overkill for this use case

**Rejected** due to size and ergonomics.

### 3. Cryptographic Hash of URL

**Pros**
- Deterministic mapping
- No counter required

**Cons**
- Same URL always produces same shortcode
- No easy way to enforce per-user quotas
- Harder to rotate or invalidate

**Rejected** due to operational inflexibility.

## Time Complexity and Latency Impact

- Shortcode generation runs in **O(1)** time
- Hashing, arithmetic, and encoding are constant-time operations
- No external calls are required during generation

Impact on request latency is negligible and well within the acceptable bounds
for the shortening (write) path.

This strategy does **not** affect the critical redirect (read) latency path.

## Consequences

### Positive
- Guaranteed uniqueness without retries
- Constant-time generation
- Predictable shortcode length
- Obfuscated internal sequencing
- Simple reasoning about correctness

### Negative
- Requires careful counter management
- Depends on retention-based expiration to safely reuse space
- Salt rotation must be handled carefully to avoid breaking determinism
- Multiplicative factor must be validated to ensure coprimality with the modulo space

## Impact

This decision directly influences:
- Data model design
- Quota enforcement strategy
- Retention and expiration policies
- Security posture against URL enumeration
- Performance characteristics of the write path

Future changes to retention duration or scale assumptions may require revisiting
shortcode length or output space size.
