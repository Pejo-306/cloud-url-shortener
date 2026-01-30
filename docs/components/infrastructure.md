# Component: `infrastructure` - SAM / CloudFormation

## Responsibility

Defines and manages the runtime infrastructure for the `cloudshortener` system.

This component owns all AWS resources required to run the application in a given environment, including networking, compute, authentication, configuration wiring, data plane resources, frontend hosting, and observability.

All infrastructure in this component is deployed declaratively via AWS SAM / CloudFormation.

## Scope of Ownership

The infrastructure stack **owns and manages**:

- Networking (VPC, subnets, routing, security groups)
- API Gateway and Lambda functions
- Cognito authentication resources
- AppConfig application and configuration profile
- ElastiCache (Redis) replication group
- Frontend hosting (S3 + CloudFront)
- Observability (X-Ray, Application Insights)
- IAM roles required for runtime execution

## Networking

### VPC
- One VPC per environment
- CIDR: `10.0.0.0/16`
- DNS hostnames and DNS support enabled

### Subnets
- Public subnet:
  - Hosts NAT Gateway
- Private subnets (two AZs):
  - Used by Lambda functions
  - Used by ElastiCache

### Routing
- Internet Gateway attached to the VPC
- NAT Gateway in public subnet
- Private subnets route outbound traffic via NAT

### Security Groups
- **LambdaSecurityGroup**
  - Allows outbound traffic
- **ElastiCacheSecurityGroup**
  - Allows inbound Redis traffic only from LambdaSecurityGroup

## Compute

### Lambda Functions

| Function | Purpose | Auth | Trigger |
|--------|--------|------|---------|
| `shorten-url-function` | Create short URLs | Cognito-protected | API Gateway |
| `redirect-url-function` | Resolve and redirect short URLs | Public | API Gateway |
| `warm-appconfig-cache-function` | Proactively warm AppConfig cache | N/A | EventBridge |

Common configuration:
- Runtime: Python 3.13 (arm64)
- Timeout: 30 seconds
- Tracing: AWS X-Ray enabled
- Logging: JSON format
- Deployed inside private subnets
- Use a shared execution role

## API Gateway

- One API Gateway per environment
- Stage name matches `AppEnv`
- CORS enabled for `GET`, `POST`, `OPTIONS`
- Default authorizer:
  - Amazon Cognito User Pool authorizer
- Explicitly unauthenticated route:
  - `GET /{shortcode}`

API Gateway is the **only ingress point** for user-facing Lambda functions.

## EventBridge

- **AppConfigDeploymentRule**: trigger AppConfig cache warm up on successful deployment

## Authentication (Cognito)

The stack provisions:

- Cognito User Pool
- Cognito User Pool Client (for frontend)

Key properties:
- Email-based users
- SDK-based authentication (via `amazon-cognito-identity-js`)
- Tokens issued for frontend authentication
- Cognito is used exclusively for API authorization (not user management beyond auth)

## Runtime Configuration (AppConfig)

The infrastructure stack creates:

- AppConfig Application
- AppConfig Environment (per `AppEnv`)
- AppConfig Configuration Profile (`backend-config`)
- Hosted configuration version
- Deployment using `AppConfig.AllAtOnce`

### Configuration Responsibility
AppConfig stores **logical configuration only**, including:
- Active backend selection
- Redis connection parameters (resolved via SSM and Secrets Manager references)

Secrets and parameter values themselves are **not owned by this stack**.

## Data Plane: ElastiCache (Redis)

- Redis replication group per environment
- Multi-AZ enabled
- Automatic failover enabled
- Encryption:
  - At-rest encryption enabled
  - In-transit encryption enabled
- Auth token sourced from AWS Secrets Manager
- Deployed in private subnets

Redis is used as the primary backend data store for the application.

## Frontend Hosting

### S3
- One bucket per environment
- Static website hosting enabled
- Versioning enabled
- Bucket access restricted via CloudFront OAC

### CloudFront
- HTTPS-only distribution
- S3 origin with Origin Access Control
- Managed cache policy
- SPA-style routing (404 → index.html)
- Regional price class

CloudFront serves the frontend and integrates with Cognito and API Gateway.

## IAM

### Lambda Execution Role

Grants access to:
- AppConfig (configuration retrieval)
- SSM Parameter Store (read-only)
- Secrets Manager (read-only)
- CloudWatch Logs
- AWS X-Ray
- VPC networking (ENI management)
- ElastiCache (Redis access for caching)

This role is **runtime-only** and does not include provisioning permissions.

## Observability

- AWS X-Ray enabled for:
  - API Gateway
  - Lambda functions
- AWS Application Insights enabled via resource group
- Log output is structured as JSON

## Inputs (Parameters)

| Parameter | Purpose |
|---------|--------|
| `AppEnv` | Target environment (`local`, `dev`, `staging`, `prod`) |
| `AppName` | Application name prefix |
| `FrontendBucketName` | Base name for frontend S3 bucket |
| `AppConfigAgentURL` | Local AppConfig agent endpoint |
| `LocalstackEndpoint` | Localstack endpoint (local only) |
| `ElastiCacheNodeType` | Redis node size |
| `ElastiCacheEngineVersion` | Redis engine version |
| `ElastiCachePort` | Redis port |

## Outputs (Contracts)

The stack exports values used by operators and other components:

- API base URL
- Frontend CloudFront URL
- Cognito User Pool and Client IDs
- AppConfig identifiers
- CloudFront distribution ID (for invalidation)
- Redis primary and reader endpoints

These outputs form the **public contract** of the infrastructure stack.

## Boundaries and Non-Goals

This component explicitly does **NOT** manage:

- Bootstrapping scripts or bootstrap CloudFormation stacks
- Seeding or rotating secrets and SSM parameters
- CI/CD IAM trust configuration (OIDC bootstrap responsibility)
- Application code behavior
- External data backups or migrations

Those concerns are handled by the [bootstrap](/docs/components/bootstrap.md) or runtime components.

## Deployment Model

- Deployed using AWS SAM
- One stack per environment: `{AppName}-{AppEnv}`
- Environment promotion is handled externally (CI/CD)

## Architecture Diagram

Refer to: 

![Architecture Diagaram](/docs/assets/png/architecture-diagram.png)

This diagram illustrates:
- Client → CloudFront → S3
- Client → API Gateway → Lambda → Redis
- Cognito-based authentication flow
- AppConfig-based runtime configuration
