# ADR-017: Deploy `cloudshortener` on GCP

## Status

Accepted

## Date

2026-04-19

---

## Context

Today `cloudshortener` deploys and runs exclusively on AWS. The original cloud provider decision ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md)) rejected GCP due to unfamiliarity with the ecosystem. I'm doing this initiative to eliminate this constraint.

This document details the high-level changes we need to support GCP deployment, including:
- Infrastructure modeling (GCP equivalents for AWS services)
- Organizational and IAM modeling
- Configuration and secrets management
- Backend and frontend refactoring
- DevOps tooling and CI/CD extensions
- Adjacent infrastructure (OIDC and bastion stacks)

We'd like to support deployment on GCP as a first-class cloud provider alongside AWS. We treat both equally in our codebase, tooling, CI/CD pipelines.

This document finishes with a high-level migration plan.

## Infrastructure Modeling

Some AWS services and infrastructure have 1-to-1 mapping, some don't. The tables below detail the GCP equivalents and rationales behind this modeling.

### Service Mapping

| AWS Service | GCP Equivalent | Notes |
|-------------|---------------|-------|
| AWS Lambda | **Cloud Functions (gen 2)** | Same concept as Lambda's single-handler model. Gen 2 required for VPC connector support and Eventarc triggers. |
| API Gateway (REST) + Cognito Authorizer | **Cloud API Gateway** + OpenAPI 2.0 spec | Routes and JWT validation are expressed declaratively in an OpenAPI spec. Infra-only change; function code is unaffected. |
| Amazon Cognito (User Pool + Client) | **Identity Platform** (Firebase Auth) | Provides same user pools and email/password flows as Cognito. Cloud API Gateway validates tokens at the edge. |
| ElastiCache (Redis, single-shard replication group) | **Memorystore for Redis, Standard** | HA with primary + replica, automatic failover, private IP. Matches our single-node, single-replica topology. |
| S3 + CloudFront (frontend distribution) | **Cloud Storage bucket + HTTPS Load Balancer + Cloud CDN** | SPA fallback (403/404 → `index.html`) is handled by URL map error rules on the LB. |
| AWS AppConfig + EventBridge + warm Lambda | **Cloud Storage (versioned bucket) + Eventarc (`object.finalized`) + Cloud Function** | Config JSON uploaded to GCS triggers a warm function that loads it into Memorystore. Replaces AppConfig agent + EventBridge wiring. |
| Parameter Store | **Cloud Function environment variables** (non-secret) or **Secret Manager** (if runtime reads are needed) | GCP has no direct "parameter store" product. |
| Secrets Manager | **GCP Secret Manager** | Near-identical: versioned secrets, IAM access control, SDK reads at runtime. |
| EventBridge (rules + targets) | **Eventarc** | Routes events to Cloud Functions (gen 2) targets. Same concept as EventBridge. |
| VPC + subnets + IGW + NAT + SGs | **VPC network + regional subnets + Cloud NAT + firewall rules** | See networking section below. |

### Networking

GCP networking achieves the same isolation as our AWS VPC stack, with some structural differences:

| AWS Resource | GCP Equivalent | Notes |
|-------------|---------------|-------|
| VPC (`10.0.0.0/16`) | **VPC network** | GCP VPCs are global; subnets are regional. |
| Public subnet + IGW + public route | No separate resource | No IGW concept in GCP. Cloud NAT does not need a "public subnet" host. Fewer resources to manage. |
| 2 private subnets (2 AZs) | **1 regional subnet** | A single GCP subnet already spans all zones in the region. Two subnets only needed for logical separation (app vs data tier), not for multi-zone redundancy. |
| NAT Gateway + Elastic IP | **Cloud NAT** + **Cloud Router** | Same pattern: outbound-only internet for private workloads. Optional static IPs replace the Elastic IP. |
| Security groups (stateful, per-ENI) | **VPC firewall rules** | Stateful, target by tag or service account. Same intent: "only Cloud Functions connector may reach Memorystore on 6379." |
| Lambda ENIs in VPC | **Serverless VPC Access connector** | Cloud Functions (gen 2) use a connector to reach private resources like Memorystore. |
| ElastiCache subnet group | **Memorystore VPC + IP range config** | No separate "subnet group" resource; Memorystore is placed in the VPC directly. |

### Configuration and Secrets

On AWS we use three services for configuration ([ADR-006](/docs/decisions/ADR-006-configuration-management.md)). On GCP:

| AWS Service | GCP Replacement | Rationale |
|-------------|----------------|-----------|
| AppConfig (versioned config documents) | **Cloud Storage** (versioned bucket with config JSON) | No direct AppConfig equivalent on GCP. GCS versioning + Eventarc trigger replaces the deployment + warm-cache pipeline. |
| Parameter Store (non-secret values) | **Cloud Function environment variables** at deploy time | Simple, no extra service. |
| Secrets Manager (credentials) | **GCP Secret Manager** | Near-identical API and operational model. |

The `warm_appconfig_cache` Lambda becomes a Cloud Function triggered by `google.cloud.storage.object.v1.finalized` on the config bucket.

### Alternatives Considered

Here I've listed alternative solutions for some AWS services which don't map cleanly 1-to-1 with GCP equivalents.

| AWS Service | Chosen GCP Equivalent | Alternative Considered | Rejection Rationale |
|-------------|----------------------|----------------------|---------------------|
| AWS Lambda | Cloud Functions (gen 2) | Cloud Run | Cloud Run is container-first; requires packaging a full HTTP server image per function. Our Lambdas are single-handler, not long-running servers. Cloud Functions maps closer to our current model. |
| API Gateway + Cognito Authorizer | Cloud API Gateway | HTTPS Load Balancer + URL map | LB + URL map works but lacks native JWT validation at the gateway level. Would push auth into function code or require extra wiring. Cloud API Gateway handles JWT via OpenAPI spec declaratively. |
| Amazon Cognito | Identity Platform | Firebase Auth (standalone) | Identity Platform and Firebase Auth share the same backend. Identity Platform is the GCP-native product name with enterprise features and better fit for API Gateway JWT integration. Functionally equivalent; we refer to both interchangeably. |
| ElastiCache (single-shard replication group) | Memorystore for Redis, Standard | Memorystore for Redis Cluster | Cluster is sharded (multi-primary, distributed keyspace). Our topology is `NumNodeGroups: 1` with one replica. Standard tier matches this exactly. Cluster adds complexity and client constraints we do not need. |
| CloudFront + S3 | HTTPS LB + Cloud CDN + Cloud Storage | Firebase Hosting | Firebase Hosting is simpler (single config file, built-in CDN + HTTPS + SPA rewrites) but may lock us into limitations of a done-for-you service (if we need something, Firebase hosting must support it). Viable alternative; may revisit if operational simplicity outweighs flexibility. |
| AppConfig + EventBridge + warm Lambda | Cloud Storage (versioned) + Eventarc + Cloud Function | Unleash / flagd on Cloud Run | Our AppConfig usage is a single versioned JSON config document, not feature flags. Running a self-hosted service for one config blob adds a container to maintain and a cost floor. GCS + Eventarc achieves the same with zero extra infrastructure. |
| AppConfig + EventBridge + warm Lambda | Cloud Storage (versioned) + Eventarc + Cloud Function | Firestore document | Viable for small config. Rejected because GCS versioning + Eventarc trigger gives us the same deploy-and-warm pipeline with simpler event wiring and no Firestore dependency. |
| Parameter Store | Cloud Function env vars / Secret Manager | Firestore or GCS for runtime reads | Our parameter values are set at deploy time and rarely change. Environment variables are the simplest delivery mechanism. If runtime reads become necessary, Secret Manager already covers it. |

## Organizational and IAM Modeling

### Account → Project

In AWS, we have a single AWS account where we deploy a separate CloudFormation stack per environment (`dev`, `staging`, `prod`).

In GCP, the equivalent is having one GCP project per environment (e.g. `cloudshortener-dev`, `cloudshortener-staging`, `cloudshortener-prod`). A GCP project provides structural isolation for IAM, billing, infrastructure components, same as AWS CloudFormation.

Our GCP projects will be long-lived. Our tooling should idempotently create projects (if they don't exist), enable GCP APIs, and deploy infrastructure resources in them. But our tooling should not be able to delete projects due to billing concerns. We destroy GCP projects manually if desired.

### IAM

AWS IAM roles with inline/managed policies translate to *GCP service accounts with IAM role bindings*.

| AWS Concept | GCP Equivalent |
|------------|---------------|
| Lambda execution role (trusted by `lambda.amazonaws.com`) | **Service account** attached to the Cloud Function |
| Inline/managed policies listing actions + resources | **IAM bindings**: grant predefined or custom roles to the service account on specific resources or at project level |
| Resource policy on Lambda (who can invoke) | **`roles/cloudfunctions.invoker`** binding on the function: `allUsers` for redirect (public), API Gateway SA for shorten (protected), Eventarc SA for warm (event-triggered) |
| Bastion role + instance profile | **Service account** on the Compute Engine VM (no instance profile wrapper needed; GCP VMs reference SAs directly) |

### Required permissions for Cloud Functions service account

| Permission area | GCP role / binding |
|----------------|-------------------|
| Read secrets | `roles/secretmanager.secretAccessor` on relevant secrets |
| Read config from GCS | `roles/storage.objectViewer` on the config bucket |
| Write logs | Typically implicit via default behavior; explicit via `roles/logging.logWriter` |
| VPC connector access | Granted via connector configuration |

## Backend and Frontend Refactoring

### Backend

- Add common cloud provider interface
- Decouple shorten and redirect flow from AWS lambdas
- AWS lambda handlers and GCP cloud functions are only responsible for accepting request & parsing response to JSON
- Replace `boto3` with `google-cloud-*` packages for GCP paths
- Segment dependencies into per-provider groups so the codebase works with either set installed

### Frontend

- Replace `amazon-cognito-identity-js` with `firebase/auth` (Identity Platform client SDK)
- Same per-provider dependency segmentation as backend
- Update frontend config to support Identity Platform project ID / API key

### Events

- Refactor test event payloads in `/events` to GCP Cloud Functions format

## DevOps Tooling and CI/CD Extensions

### Tooling

- Make targets support a cloud provider argument (`aws`, `gcp`, or list with both)
- Extract make recipes into standalone bash scripts for reuse in GHA and locally
- GCP infrastructure is managed via Terraform

### CI/CD

- All workflows except our codebase code checks receive `cloud_providers` input parameter (list of `aws`, `gcp` or both)
- Template linting in AWS stays `sam validate --lint`. In GCP we do `terraform validate` + `terraform fmt -check`
- Code checks remain unchanged
- Test suite (integration tests & future tests) are parametrized by cloud provider. We only run tests for selected providers.
- CI builds Cloud Functions artifacts for GCP
- CD deploys to selected cloud providers
- GitHub actions authenticate to GCP via Workload Identity Federation (same OIDC concept)
- We need to add a file in our repository with parameter defaults for our automated workflows

### Infrastructure as Code

AWS continues to use *SAM/CloudFormation*. GCP uses *Terraform*.

Terraform templates are placed alongside AWS templates at the most granular level
(e.g. `infra/stacks/network/gcp/`, `infra/stacks/backend/gcp/`). AWS templates
move to `aws/` subdirectories.

GCP projects are created if non-existent by Terraform. We explicitly prevent Terraform from destroying GCP projects.

GCP API enablement is handled in Terraform.

## Adjacent Infrastructure

### OIDC Stack

GitHub Actions authenticates to GCP using *Workload Identity Federation*, the direct equivalent of the AWS OIDC bootstrap stack.

| AWS Resource | GCP Equivalent |
|-------------|---------------|
| `AWS::IAM::OIDCProvider` (GitHub token endpoint) | **Workload Identity Pool + OIDC Provider** |
| `GitHubOidcDeployRole` (deploy identity) | **Deploy service account** impersonated via WIF, scoped to repo + branch |
| `CloudFormationExecRole` + exec policies | No direct equivalent. Terraform runs as the deploy SA directly. IAM bindings on the deploy SA grant resource-creation permissions. |
| `IntegrationTestsExecutorRole` | **Test service account** impersonated via WIF, with test-specific bindings |

The OIDC stack is defined as a Terraform template.

The key difference is that in AWS we use multiple IAM roles to deploy stacks and allow CloudFormation to CRUD resources. In GCP we only have one service account to do both.

### Bastion Host

Bastion stack and purpose remain the same: a VM to allow outside users (like integration tests) connect to our MemoryStore instances.

| AWS Resource | GCP Equivalent |
|-------------|---------------|
| EC2 instance (private subnet, no public IP) | **Compute Engine VM** (private subnet, no external IP) |
| SSM Session Manager (port forwarding) | **Identity-Aware Proxy (IAP) TCP tunneling** (`gcloud compute start-iap-tunnel`) |
| Bastion role + `AmazonSSMManagedInstanceCore` | **Service account** with IAP-related permissions |
| Instance profile | Not needed; GCP VMs reference service accounts directly |

Bastion stack is managed via Terraform in a separate template.

## Local Development

On AWS we use `sam local start-api`. On GCP the equivalent is the **`functions-framework`** (Python) for running Cloud Functions locally.

No changes to the local Docker Compose / Localstack setup for AWS.

## Migration Plan

1. Write Terraform templates for GCP infrastructure
2. Automate infrastructure setup via Make tooling
3. Extract Make recipes into standalone bash scripts
4. Update bootstrap scripts to work with GCP (seed parameters & secrets)
5. Set up OIDC stack (Workload Identity Federation) via Terraform
6. Extend CI/CD workflows to accept cloud provider parameter
7. Refactor backend to work with GCP
8. Refactor frontend to use Identity Platform (`firebase/auth`)
9. Extend integration tests to work with GCP infrastructure

## Implications

On the plus side, I gain hands-on experience with GCP's ecosystem.

Provider-agnostic abstractions will improve codebase quality.

As a negative, we increase infrastructure and tooling complexity since we need to support multiple first-class cloud providers. It will take more effort to develop and maintain the application going-forward.

Furthermore, we should stray away from AWS-only services going forward like AppConfig. The more generic services we use, the easier it is to support both cloud provider deployments.

## Impact

This decision directly influences:
- Infrastructure definition and tooling ([ADR-002](/docs/decisions/ADR-002-cloud-provider.md))
- Compute model ([ADR-005](/docs/decisions/ADR-005-serverless-compute.md))
- Configuration management ([ADR-006](/docs/decisions/ADR-006-configuration-management.md))
- Authentication model ([ADR-010](/docs/decisions/ADR-010-authentication-model.md))
- CI/CD strategy ([ADR-012](/docs/decisions/ADR-012-continuous-integration-and-development.md))
- Integration testing ([ADR-016](/docs/decisions/ADR-016-integration-tests.md))
- Codebase structure, dependency management, and local development workflow

Future changes to supported cloud providers would extend this pattern.
