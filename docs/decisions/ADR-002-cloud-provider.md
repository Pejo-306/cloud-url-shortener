# ADR-002: Cloud Provider Selection

## Status

Accepted (Retroactively documented)

## Date

2025-12-21

## Context

The `cloudshortener` system is designed to run in a public cloud environment 
([C-1](/docs/requirements.md#c-1-cloud-environment)) and was implemented as a
3-week MVP by a single engineer - Pesho ([C-2](/docs/requirements.md#c-2-time-constraints), 
[C-3](/docs/requirements.md#c-3-team-size)).

Relevant requirements and constraints:
- Prefer fully managed and serverless services ([NFR-3](/docs/requirements.md#nfr-3-availability))
- Free resources available for learning purposes ([NFR-6](/docs/requirements.md#nfr-6-cost-awareness))
- Support rapid iteration and experimentation
- Redis Cloud is used as a primary datastore and can only be deployed on 
**AWS/GCP** ([ADR-001](/docs/decisions/ADR-001-primary-datastore.md))

The system requires:
- Serverless compute
- Managed authentication
- Managed networking and observability
- Tight integration between managed services

Also, the project was explicitly intended as a **learning exercise** for cloud-native
system design.

## Decision

Use **Amazon Web Services (AWS)** as the cloud provider for hosting the `cloudshortener`
system.

The system relies on:
- Serverless compute service (**AWS Lambda Functions**)
- Fully managed networking and infrastructure components
- Managed authentication services (**Amazon Cognito**)
- Managed configuration services (**AWS AppConfig, AWS Parameter Store, AWS Secrets**)

Additionally, these components either add convenience or will be useful in the future:
- Infrastructure as Code offering (**AWS CloudFormation and AWS Serverless Application Model**)
- Managed caching replication group (**AWS ElastiCache**)
- Edge location distribution for frontend application (**AWS CloudFront**)
- General, cheap, highly durable storage for backups, hosting web apps, etc. (**AWS S3**)

## Alternatives Considered

### 1. Google Cloud Platform (GCP)

**Pros**
- Supports Redis Cloud deployments
- Strong managed services and global networking
- Competitive serverless offerings

**Cons**
- No familiarity with the ecosystem (when I started this project)
- Less mature than AWS
- Smaller array of services compared to AWS

**Rejected** in favor of AWS due to familiarity and broader service ecosystem.

### 2. Microsoft Azure

**Pros**
- Mature cloud platform
- Strong enterprise integration

**Cons**
- Microsoft
- Redis Cloud is not natively supported on Azure

**Rejected** due to being Microsoft.

### 3. Self-Hosted Cloud / Virtual Machines

**Pros**
- Full control over infrastructure
- Lower long-term costs
- Opportunity to optimize infrastructure for the system's needs

**Cons**
- Complete overkill for a single engineer - Pesho - creating a 3-week MVP
- No serverless / managed-services offerings
- Distracts learning experience from system design focus.

## Consequences

### Positive
- Minimal infrastructure management overhead
- Rapid CI/CD via serverless services
- Tightly integrated, out-of-the-box managed services for authentication and configuration
- Behind-the-scenes horizontal scaling
- Compatibility with Redis Cloud as the primary datastore

### Negative
- Vendor lock-in to AWS-specific services
- Cloud-native abstractions don't translate directly to other cloud providers
- Challenging to predict costs at scale

## Impact

This decision directly influences:
- Compute model (serverless in favor of long-running services)
- Authentication and authorization is outsourced to cloud vendor
- Configuration and secrets management
- Deployment and CI/CD tooling
- Observability and monitoring strategies

Subsequent ADRs build on AWS-managed services and their operational characteristics.
