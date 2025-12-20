# System Architecture

This document describes the **high-level architecture** of the `cloudshortener` system.

It describes **system architecture, responsibility boundaries, and request flows**.
The rationale behind specific design choices is documented in Architectural Decision
Records (ADRs).

## 1. System Overview

`cloudshortener` is a cloud-based URL shortening service of a small number of
stateless compute components backed by a centralized data store.

The system exposes:
- A **public redirect interface**, optimized for low-latency reads
- An **authenticated write interface** for creating short URLs

The architecture is designed to favor:
- Fast read performace
- Easy horizontal scalability
- Minimal operational overhead

## 2. High-Level Components

![Architecture Diagram](/docs/assets/png/architecture-diagram.png)



### 2.1 API Gateway (Ingress)

The system exposes HTTP endpoints via a single API ingress layer.

Responsibilities:
- Route requests
- Enforce authentication for protected endpoints
- Integration with backend compute components

### 2.2 Redirect Service (Read Path)

A stateless compute component responsible for resolving shortcodes.

Responsibilities:
- Accept public redirect requests
- Resolve shortcodes to long URLs
- Enforce link hit access limits
- Issue HTTP redirects

This component lies on the **critical latency path** and is optimized for read
performance.

### 2.3 Shortening Service (Write Path)

A stateless compute component responsible for creating new short URLs.

Responsibilities:
- Accept authenticated requests
- Generate unique shortcodes
- Enforce 1:1 mapping between shortcode and long URL
- Persist link mappings
- Enforce user-level quotas

Latency is less critical for this component compared to the redirect service.

### 2.4 Data Store

A centralized data store to persist link mappings, metadata, etc.

Responsibilities:
- Store shortcode-to-URL mappings
- Track user quotas
- Track link access limits
- Enforce data expiration via retention policies

The data store is access by both read and write paths and represents the primary
stateful dependency in the system.

### 2.5 Configuration and Secrets Management

Used to supply runtime configuration and secrets to compute components.

Responsibilities:
- Provide environment-specific configuration
- Allow configuration updates without redeployment
- Protect sensitive credentials

### 2.6 Authentication Providers

An authentication provider is used to authenticate users acessing protected 
endpoints.

Responsibilities:
- User identity management
- Token issuance and validation
- Authentication integration with the API ingress

### 2.7 Caching Layer

A high-speed cache is used reduce lambda execution time by caching HOT values.

Responsibilities:
- Cache application configurations for fast access

## 3. Request Flows

### 3.1 Redirect Flow (Read)

1. Client issues a `GET` request to a `short URL`
2. Request is routed through the API ingress
3. Redirect service resolves the shortcode
4. `long URL` is retrieved from the data store
5. Client is redirected via HTTP `302`

The flow is designed to minimize latency and external dependencies.

### 3.2 Shortening Flow (Write)

1. Authenticate client submits a `long URL`
2. Request is routed through the API ingress
3. Shortening service validates request and user quota
4. A unique shortcode is generated
5. Link mapping is persisted in the data store
6. Short URL is returned to the client

This flow prioritizes correctness and durability over latency.

## 4. Data Ownership and Responsibilities

- The data store is the **single source of truth** for all persisted data.
- Compute components are stateless and do not retain data between requests.
- Quotas and limits are enforced at request time based on stored state.

## 5. Failure Isolation

The architecture is designed such that:

- Failures in the write path do not impact redirect availability
- Authentication failures do not affect public redirect access
- Individual compute instances may fail without state loss

Failure handling and recovery strategies are documented in seperate decision
records and operational documentation.

## 6. External Dependencies

The system depends on the following external services:
- Cloud provider-managed compute and networking resources
- Managed cloud-based data storage service
- Cloud provider-managed authentication service

These dependencies are treated as **highly available and scalable** components.

## 7. Out-of-Scope Architecture

The following architectural concerns are intentionally not addressed here:
- Analytics pipeline
- Frontend application and distribution
- Billing or monetization services
- Abuse detection systems
- Multi-region active-active replication

These may be introduced in future iterations.

## 8. Relationship to Other Documents

- [requirements.md](/docs/requirements.md) defines the constraints this architecture satisfies
- [decisions/](/docs/decisions/) contains rationale for key design choices
- Operational an deployment details are documented elsewhere
