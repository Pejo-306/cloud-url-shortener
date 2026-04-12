# `infrastructure` — Infrastructure as Code

Declarative templates under [`infra/`](../../infra/) compose a root stack and nested stacks by component (network, identity, configuration, cache, backend, frontend). The templates are self-contained, complete, and managed by IaC tools.

## Stacks

| Stack | Purpose | Template |
|-------|---------|----------|
| `network` | Private network, subnets, routing, and perimeter rules. | [`stacks/network/template.yaml`](/infra/stacks/network/template.yaml) |
| `cognito` | User directory and tokens for authenticated API routes. | [`stacks/cognito/template.yaml`](/infra/stacks/cognito/template.yaml) |
| `appconfig` | Runtime configuration registry and deployment lifecycle. | [`stacks/appconfig/template.yaml`](/infra/stacks/appconfig/template.yaml) |
| `elasticache` | Managed Redis for application caching. | [`stacks/elasticache/template.yaml`](/infra/stacks/elasticache/template.yaml) |
| `backend` | Edge API, serverless handlers, and runtime permissions. | [`stacks/backend/template.yaml`](/infra/stacks/backend/template.yaml) |
| `frontend` | Static asset bucket and CDN in front of the SPA. | [`stacks/frontend/template.yaml`](/infra/stacks/frontend/template.yaml) |
| `bastion` | Jump host for operator access into the private network. | [`bastion/template.yaml`](/infra/bastion/template.yaml) |

## Bootstrap

A separate stack ([`infra/bootstrap/template.yaml`](../../infra/bootstrap/template.yaml)) wires CI to the cloud provider account via federated identity.

We have bootstraping scripts in [`infra/bootstrap/scripts/`](../../infra/bootstrap/scripts/) which seed parameters, secrets, and cache data the nested stacks do not create—see [`infra/bootstrap/README.md`](../../infra/bootstrap/README.md) for how to run them.

## Architecture diagram

![Architecture diagram](/docs/assets/png/architecture-diagram.png)

## Further reading

- [Requirements](../requirements.md) — functional and non-functional constraints
- [Architecture](../architecture.md) — system design and major components
- [Decisions](../decisions/) — architectural decision records (ADRs)
- [`infra/`](../../infra/) — templates, Makefiles, bootstrap
