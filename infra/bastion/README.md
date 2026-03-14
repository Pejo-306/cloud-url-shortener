# SSM bastion

Ephemeral EC2 bastion host with AWS SSM (Systems Manager) for port-forwarding to VPC resources. Typically used to connect securely to ElastiCache, e.g. in integration tests.

Deployed into the cloudshortener VPC private subnet, reusing the Lambda security group. CloudFormation guarantees SSM readiness.

You can create and manage the bastion host via the [infra/bastion Makefile](./Makefile).

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) v2
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) for AWS CLI
- Deployed `cloudshortener` orchestrator stack

## Usage

Bastion management:

```bash
# Deploy bastion
make up

# Start SSM port-forwarding to VPC resources. Keep this session open.
# Use other terminal sessions to connect and interact with VPC resources.
make connect

# Tear down bastion when done
make down
```

Connect to VPC resources, e.g.:

```bash
# In another terminal, connect to ElastiCache
export ELASTICACHE_USERNAME="default"
export ELASTICACHE_PASSWORD="<your-password>"
redis-cli --tls --insecure -u rediss://$ELASTICACHE_USERNAME:$ELASTICACHE_PASSWORD@localhost:16379
```
