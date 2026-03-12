# ADR-016: Backend integration tests for `cloudshortener`

## Status

Accepted

## Date

2026-03-12

## Context

We would like to add integration tests to assert components interact **as expected** in real AWS infrastructure. This saves us a lot of manual infrastructure deploying and testing we would need to do to verify new features / initiatives work. Also saves us from component regressions.

For integration tests we assume the perspective of a developer who wants to assert:
- How X feature affects Y's component state?
- Are internal component mechanisms functioning properly?
- Can our backend realize an end-to-end shortening and redirection technical flow?

## Technical details

### What are we testing

| Test | Flow | Reasoning |
|------|------|------------|
| Happy E2E path | authenticate -> shorten URL -> redirect via shortlink | Validate backend system E2E |
| Unauthorized shorten | DON'T authenticate -> shorten URL -> 401 | Cognito authorizer is wired to API gateway |
| Nonexistent shortcode | try to access non-existent URL -> Error | Error path works correctly against real infra and data store |
| CORS headers present | shorten / redirect URL -> assert CORS headers | Could break between envs |
| Config warming | Deploy new AWS AppConfig version -> cache warmer lambda is triggered -> ElastiCache seeded | Critical reliability and optimization mechanism |
| User quota tracking | shorten URL -> assert quota key is present & changed | Proper handler & DB wiring + real time |
| Link hit quota tracking | redirect URL -> assert quota key is present & changed | Proper handler & DB wiring + real time |
| DAO contract fulfillment | shorten & redirect handlers with different DAOs -> different DB states | DAO contract is fulfilled |
| Non conflicts | Shorten same URL twice (duplicate request) -> get 2 different responses with different shortlinks | Doesn't introduce hidden caching mechanism |

### What are we NOT testing

- E2E user flows from the perspective of an end user
- Integration with our frontend
- Non-functional requirements
- Chaos resiliency

### Where

The developer can run integration tests locally and they require a full `cloudshortener` stack available in AWS. Tests run on real AWS infra, NOT on testcontainers, separate containers, Docker Compose, mocked services, etc.

CD pipeline should also run these tests.

### When

Our CD pipeline runs integration tests in `cloudshortener-staging` after CD successfully deploys to AWS.

## Alternatives considered

### 1. Testcontainers / Docker Compose stack

**Pros:**
- Lightweight
- Easy to run both locally and in CI without real AWS infra

**Cons:**
- Don't have authentic containers for all AWS services
- Not testing in a real AWS environment -> subtle differences slip through

**Rejected** because our system wouldn't run in a real AWS environment with real constraints.

## Requirements

### Criteria for success

I deploy my AWS stack. I run `make integration-tests` from my repository root - it sets up a bastion host, runs integration tests, then cleans up my bastion host. Tests pass. My deployed environment remains unchanged. I can rerun `make integration-tests` multiple times idempotently.

My CD pipeline succeeds deploying to `cloudshortener-staging`. The pipeline triggers a new job which runs integration tests on AWS infra. Tests succeed. If tests were to fail, I'd get a report on what failed.

After integration tests pass, I know I can confidently trigger / enable / disable various features covered by these tests.

### Constraints

#### C-1: Requires full `cloudshortener` stack deployed in AWS

#### C-2: Integration tests should be runnable both locally and in CD pipeline

#### C-3: Configuration: only thing that should be configurable is the name of the AWS stack + AWS credentials

#### C-4: CD doesn't have direct access to VPC resources (e.g. ElastiCache)

Options are:
1. Create an EC2 bastion host and port-forward via SSH
2. Create an EC2 bastion host and port-forward via AWS SSM
3. Create a new AWS lambda and run tests inside it
4. Use AWS CodeBuild

TL;DR: Option (2) provides the best balance between native AWS security, setup simplicity, learning curve.

#### C-5: CD runners must have backend store credentials

### Assumptions

#### A-1: Full unit test suite & deployment to AWS (via CD) is a prerequisite
#### A-2: `cloudshortener-staging` is NOT in use during testing period
#### A-3: `cloudshortener-staging` accepts data loss and/or component failure (we can write to its backend data store)
#### A-4: Backend store for `staging` / other environment is up and running

### Triggers for new integration tests

- New feature
- New architectural component
- API contract change
- New variant of a feature (e.g. new supported backend data store)

## Implementation notes

### Tooling

In `backend/Makefile` we would like to add the following recipes:
- `setup-bastion`: sets up a minimal EC2 bastion host with AWS SSM agent
- `integration-tests`: runs `pytest` integration tests; requires bastion host parameters as `make` variables
- `teardown-bastion`: destroys EC2 bastion host

Recipes should be *idempotent* and output all needed parameters to connect via bastion host.

Recipes should not be inter-connected as requirements between each other: we rely on the dev / CD pipeline to setup & cleanup.

Our CD pipeline calls a new GHA job `integration-tests` which:
- Assumes new IAM role for integration tests
- Sets up a bastion host
- Port-forwards via SSM
- Runs integration tests
- Reports test results
- Tears down bastion host

- To address [A-4](#a-4-backend-store-for-staging--other-environment-is-up-and-running) we perform a precheck before the new `integration-tests` job which healthchecks our external Redis / other backend

### IAM permissions for EC2 bastion host

To solve [C-4](#c-4-cd-doesnt-have-direct-access-to-vpc-resources-eg-elasticache) I've decided to deploy an EC2 bastion host in one of my private subnets and port-forward via AWS SSM.

Locally, we can use AWS dev credentials to run our integration tests.

Our CD pipeline runners will need additional IAM permissions to use SSM like:

```yaml
SSMIntegrationTestRole:
  Type: AWS::IAM::Role
  Properties:
    AssumeRolePolicyDocument: { ec2.amazonaws.com service principal }
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

SSMInstanceProfile:
  Type: AWS::IAM::InstanceProfile
  Properties:
    Roles: [!Ref SSMIntegrationTestRole]
```

We will also need SSM / Secrets Manager **READ-ONLY** permissions to access backend data store credentials. Needed to solve [C-5](#c-5-cd-runners-must-have-backend-store-credentials).

### Test behavior

- Integration tests may and should directly interact with AWS resources
- Integration tests may inspect the state of data stores
- Integration tests may **NOT** patch / mock components or parts of components, either internal or external
- Integration tests assert inputs and outputs, changes in state
- Integration tests do **NOT** assert technical correctness of schema / values / edge case (that's what unit tests are for)

### PoC

No PoC is needed. I've already connected to VPC resources via a bastion EC2 host and SSH. The flow will be the same, just need to use SSM instead of SSH.

Integration tests interact with full components (lambda handlers, data stores, etc.). Should be simple enough to not have any hidden, unexpected issues.
