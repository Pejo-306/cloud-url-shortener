0- GCP creds

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/Users/petar.nikolov/Programs/cloud-url-shortener/infra/gcp/gcp_creds.json" 
```

0- Env vars

```bash
export APP_NAME=cloudshortener
export APP_ENV=dev
export REGION=europe-west1

export ADMIN_PROJECT_ID=cloudshortener-admin
export ENV_PROJECT_ID=cloudshortener-dev

export ADMIN_PROJECT_NUMBER="$(gcloud projects describe "$ADMIN_PROJECT_ID" --format='value(projectNumber)')"
export ENV_PROJECT_NUMBER="$(gcloud projects describe "$ENV_PROJECT_ID" --format='value(projectNumber)')"

export STATE_BUCKET=cloudshortener-tf-state-881520955141
export ARTIFACTS_BUCKET=cloudshortener-artifacts-881520955141

export ROOT_WORKLOAD_STATE_PREFIX="env/${APP_ENV}/workload"
export ROOT_PROJECT_STATE_PREFIX="env/${APP_ENV}/project"
export BASTION_STATE_PREFIX="env/${APP_ENV}/bastion"
export OIDC_STATE_PREFIX="oidc/"
```

1- Destroy bastion

```bash
cd infra/gcp/bastion

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=${BASTION_STATE_PREFIX}"

terraform destroy -var-file=terraform.tfvars
```

2- Destroy workload (network, Memorystore, config, frontend, backend)

```bash
cd infra/gcp/workload

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=${ROOT_WORKLOAD_STATE_PREFIX}"

terraform destroy \
  -var-file=terraform.tfvars \
  -target=module.backend \
  -target=module.frontend \
  -target=module.config \
  -target=module.memorystore \
  -target=module.network
```

3- Destroy project-level stack (optional; long-lived IAM / Identity Platform / secret shells)

Only if you intend to tear down the environment project prerequisites managed by [`infra/gcp/projects/`](../projects/README.md):

```bash
cd infra/gcp/projects

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=${ROOT_PROJECT_STATE_PREFIX}"

terraform destroy -var-file=terraform.tfvars
```

4- Destroy Redis Cloud secret

```bash
gcloud secrets delete "${APP_NAME}-${APP_ENV}-secret-redis-credentials" \
  --project="${ENV_PROJECT_ID}"
```

5- Destroy OIDC stack

```bash
cd infra/gcp/oidc

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=${OIDC_STATE_PREFIX}"

terraform destroy -var-file=terraform.tfvars
```

6- Empty both admin buckets, then destroy admin stack (local state)

Only after every root that used **`${STATE_BUCKET}`** for remote state has been destroyed (`oidc/`, `projects/`, `workload/`, `bastion/` above). **Emptying the state bucket deletes all remote `*.tfstate` objects** for those stacks.

```bash
gcloud storage rm --recursive --all-versions "gs://${ARTIFACTS_BUCKET}/**" || true
gcloud storage rm --recursive --all-versions "gs://${STATE_BUCKET}/**" || true

cd infra/gcp/admin
terraform init
terraform destroy -var-file=terraform.tfvars
```

Removing `google_project` (if still managed by this root) or deleting the admin project is a separate manual step in Cloud Console / `gcloud` if you need the org cleaned completely.

7- Disable APIs / destroy projects manually