# System Requirements

This document defines the **functional and non-functional requirements** for the
`cloudshortener` system.

These requirements represent the **constraints and assumptions** that drive
architectural and implementation decisions. They are intentionally technology-agnostic.

## 1. Problem Statement

Design a cloud-based URL shortener service.

The system is designed as a learning exercise in large-scale system design,
with an emphasis on real-world constraints and trade-offs.

Additionally, I chose to use AWS Lamba Functions, Python, and Redis with the
intention of learning these technologies. These technical decisions were not driven
from actual architectural decisions.

## 2. Functional Requirements

### FR-1: URL Shortening
- The system converts a long URL into a short, unique shortcode.
- Each shortcode maps exactly 1:1 with one long URL at any given point in time.

### FR-2: URL Redirection 
- Accessing a short URL redirects the client to the corresponding long URL.
- Redirects use HTTP `302 Found` (avoid browsers caching `301` due to analytics).

### FR-3: Authentication
- URL shortening is accessible only to authenticated users.
- URL redirection is publically accessible globally.

### FR-4: User Quotas
- Each authenticated user may create up to 20 short URLs per calendar month.

### FR-5: Link Hit Quotas
- Each short URL may be resolved up to 10000 times per calendar month.

### FR-6: Analytics [OPTIONAL / FUTURE]
- The system exposes analytics about link usage:
  * Total shortlink count
  * Total users count
  * % of users hitting this month's link creation quota
  * % of links hitting this month's link hit quota

## 3. Non-Functional Requirements

### NFR-1: Performance
- Redirect latency is minimal. Target: sub-second response time under normal load.
- Shortening latency is non-critical. Acceptable up to 10 seconds.

### NFR-2: Scalability
- System supports **100 million daily active users**.
- **Read-heavy workload** with an approximate **100:1** read:write ratio.
- Horizontal scaling is prefered over vertical scaling.

### NFR-3: Availability
- System must tolerate individual component failure without full outage.
- Fully-managed cloud services are prefered to inherit cloud provider's high availability.

### NFR-4: Data Retention
- Short URLs and associated metadata is retained for **1 year**.
- After the retention period, data may be automatically expired or archived.

### NFR-5: Consistency
- Redirect operation must always return the currect long URL once a shortcode is created.
- Strong consistency across regions is **NOT required**.
- Eventual consistency is acceptable where it improves scalability or availability.

### NFR-6: Cost Awareness
- The system should prioritize serverless workloads to allow on-demand provisioning and cost.
- Cost optimizations should favor read-heavy workloads.

## 4. Capacity Assumptions

These assumptions are used to guide sizing and architectural decisions.

- Daily Active Users (DAU): ~100 million
- Maximum links created per user per month: 20
- Maximum link hits per link per month: 10000
- Estimated links created per year: ~36 billion (1 link per user per month)
- Estimated size of each link entry: ~500 bytes
- Estimated annual storage requirement: ~18 TB

These are **design-level assumptions**, not guaranteed operational targets.

## 5. Constraints

### C-1: Cloud Environment
- The system is deployed in a **public cloud** environment.
- Serverless and managed services are prefered.

### C-2: Time Constraints
- The initial system was implemented as a **3-week MVP**.
- Initial design decisions were made pragmatically and documented retroactively.

### C-3: Team Size
- The system is designed and maintained by a single engineer, named Pesho.
- Speed of delivering MVP is gained over engineering seniority with a team.

## 6. Explicit Non-Goals

The following are explicitly out of scope unless stated otherwise:

- Custom domains for short URLs
- Strong global consistency guarantees
- Hard real-time analytics
- Abuse detection and spam prevention
- Monetization or billing features

## 7. Assumptions and Risks

- Traffic patters are assumed highly skewed towards reads.
- Redis eviction and TTL-based expiration are assumed to be sufficient for retention.
- Quota enforcement is best-effort and may allow brief overruns under race conditions.
