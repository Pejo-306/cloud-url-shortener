# GCP infrastructure (Terraform)

All first-class GCP infrastructure for CloudShortener lives under `infra/gcp/`. AWS/SAM templates remain under `infra/stacks/`.

## Layout

| Path | Purpose |
|------|---------|
| [`workload/main.tf`](workload/main.tf) | **Workload** root: wires stack modules (network, Memorystore, config, frontend, backend). Project creation, API enablement, Identity Platform, shared SAs, and long-lived **secret shells** live in [`projects/`](projects/README.md). |
| [`projects/`](projects/README.md) | **Project** root (per env): GCP APIs, Identity Platform + browser API key, custom service accounts, project-level IAM, Memorystore auth secret shell, Redis Cloud credentials secret shell. Apply before the workload root; state prefix e.g. `env/<env>/project`. |
| [`workload/modules/network/`](workload/modules/network/) | VPC, subnet, Cloud NAT, firewall rules, Serverless VPC Access connector. |
| [`workload/modules/memorystore/`](workload/modules/memorystore/) | Memorystore for Redis (Standard HA): **cache** for config warming (ElastiCache equivalent), not the primary datastore. Writes the auth **secret version** into a shell created by `projects/`. |
| [`workload/modules/config/`](workload/modules/config/) | Versioned GCS bucket + `backend-config.json` (AppConfig equivalent): **Redis Cloud** datastore connection (host/port/db + credentials from Secret Manager at apply time). |
| [`workload/modules/frontend/`](workload/modules/frontend/) | Frontend GCS bucket + external HTTPS (or HTTP) load balancer + Cloud CDN. |
| [`workload/modules/backend/`](workload/modules/backend/) | Cloud Functions (gen 2), API Gateway (OpenAPI), Eventarc trigger for config warm function. |
| [`admin/`](admin/) | **Bootstrap only** (local Terraform state): creates the **admin** GCP project, enables `storage.googleapis.com` + `serviceusage.googleapis.com`, and two GCS buckets (shared remote state + Cloud Function / artifact zips). Includes [`admin/placeholders/`](admin/placeholders/) — minimal function sources to zip and upload until ADR-017 step 7. Apply before any root using `backend "gcs"`. |
| [`bastion/`](bastion/) | Optional standalone stack: private Compute Engine bastion (IAP SSH tag `bastion`). |
| [`oidc/`](oidc/) | Optional standalone stack: **central** GitHub Workload Identity pool/provider in an **admin** project; per-environment `gh-deploy-*` / `gh-tests-*` service accounts and project IAM in each entry of `env_projects`. Use remote state on the shared bucket with prefix `oidc/`. |

Directories under [`workload/modules/`](workload/modules/) are **Terraform modules** consumed by the workload root. Each of **workload** (`infra/gcp/workload/`) and **project** (`infra/gcp/projects/`) defines its own `backend` block; use a **different GCS state prefix** per root (e.g. `env/dev/workload` vs `env/dev/project`).

## Project number convention

[`admin/`](admin/) does **not** take `project_number` as input: bucket names use `google_project.this.number` after the project is created.

For [`projects/`](projects/), [`workload/`](workload/), [`bastion/`](bastion/), and [`oidc/`](oidc/) (workload projects + `admin_project_number`), pass **`project_number`** explicitly where required. **Do not** read it from `data "google_project"` in those stacks: when `data.google_project.current.number` is evaluated as `(known after apply)` at plan time, IAM `member` strings derived from it become unknown too, and Terraform may schedule no-op replacements for `ForceNew` attributes.

Set it explicitly (numeric string):

```bash
gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)'
```

Use that value in **both** your [`projects/`](projects/) var file (see [`projects/terraform.tfvars.example`](projects/terraform.tfvars.example)) and your workload var file (see [`workload/terraform.tfvars.example`](workload/terraform.tfvars.example)). For OIDC, set `admin_project_number` the same way for the admin project.

## Prerequisites

1. **Workload GCP project** — project ID for [`projects/`](projects/) and [`workload/`](workload/); optional creation via `create_project` + org/billing.
2. **`admin/` bootstrap stack** — creates the shared **admin** GCP project (`google_project`), enables `storage.googleapis.com` and `serviceusage.googleapis.com`, and two GCS buckets (Terraform remote state + function source zips). Terraform state for this root is **local** under `admin/`. Copy [`admin/terraform.tfvars.example`](admin/terraform.tfvars.example), then run `terraform init && terraform apply`.

   ```bash
   cd infra/gcp/admin
   cp terraform.tfvars.example terraform.tfvars
   # admin_project_id, org_id, billing_account, optional bucket base names + region.
   terraform init && terraform apply

   export STATE_BUCKET="$(terraform output -raw state_bucket_name)"
   export ARTIFACTS_BUCKET="$(terraform output -raw artifacts_bucket_name)"
   ```

3. **Project-level Terraform** — APIs, Identity Platform, SAs, project IAM, Memorystore auth secret shell, Redis Cloud credentials secret shell. Init with prefix e.g. `env/dev/project`. See [`projects/README.md`](projects/README.md). **Apply before** the workload root. Copy outputs (`functions_sa_email`, `api_gateway_runtime_sa_email`, `eventarc_trigger_sa_email`, `memorystore_auth_secret_id`) into workload tfvars. Pass `${STATE_BUCKET}` from `admin/` outputs.

4. **Remote state for workload** — pass bucket + workload prefix at init (e.g. `env/dev/workload`):

   ```bash
   cd infra/gcp/workload
   terraform init \
     -backend-config="bucket=${STATE_BUCKET}" \
     -backend-config="prefix=env/dev/workload"
   ```

5. **Redis Cloud (primary datastore)** — Before workload `terraform apply`, seed a Secret Manager **version** with credentials into the secret shell created by the project root. See [Manual one-time setup](#manual-one-time-setup) for `gcloud` commands. Set `redis_cloud_host` (and optional port/db) in your workload var file (see `workload/terraform.tfvars.example`).

6. **Function source archives** — Zip the placeholder sources under [`admin/placeholders/functions/`](admin/placeholders/functions/) and upload to `gs://{artifacts_bucket}/{app_env}/cloud-functions/` as `shorten.zip`, `redirect.zip`, `warm.zip` (object names must match [`workload/modules/backend/locals.tf`](workload/modules/backend/locals.tf)). Entry points: `shorten_url`, `redirect_url`, `warm_appconfig_cache` (see [`admin/placeholders/README.md`](admin/placeholders/README.md)). These are **wiring stubs** until ADR-017 step 7. Set `artifacts_bucket` in workload tfvars to the **artifacts_bucket_name** output from `admin/`. Upload commands are in [Manual one-time setup](#manual-one-time-setup).

7. **OIDC / GitHub Actions (optional)** — [`oidc/`](oidc/) provisions Workload Identity Federation in **`admin_project_id`** and deploy/tests service accounts in each **`env_projects`** workload project. Copy [`oidc/terraform.tfvars.example`](oidc/terraform.tfvars.example), set admin + env project IDs and `admin_project_number`. Store state in the bucket created by **`admin/`** using backend prefix **`oidc/`**. By default this stack enables IAM/WIF-related APIs on the admin project only; workload project API enablement is owned by **`infra/gcp/projects/`** unless you set `enable_env_project_apis = true` in OIDC.

## Manual one-time setup

Run these only when you choose to (they use `gcloud` / `gsutil` and affect cloud resources). They are **not** required for local `terraform validate`.

### Redis Cloud credentials in Secret Manager

The project root creates the secret shell. Seed the secret value before applying the workload root:

```bash
export PROJECT_ID=your-gcp-project-id
export APP_NAME=cloudshortener
export APP_ENV=dev
export SECRET_NAME="${APP_NAME}-${APP_ENV}-secret-redis-credentials"

printf '{"username":"%s","password":"%s"}' "$REDIS_USER" "$REDIS_PASS" \
  | gcloud secrets versions add "$SECRET_NAME" \
      --project="$PROJECT_ID" \
      --data-file=-
```

### Upload placeholder Cloud Function zips

From the repo root (requires `zip` and `gsutil`; zips must match `shorten.zip` / `redirect.zip` / `warm.zip`):

```bash
export FUNCTION_SOURCE_BUCKET=your-artifacts-bucket
export APP_ENV=dev

cd infra/gcp/admin/placeholders/functions
for fn in shorten redirect warm; do
  ( cd "$fn" && zip -r "../${fn}.zip" . )
  gsutil cp "${fn}.zip" "gs://${FUNCTION_SOURCE_BUCKET}/${APP_ENV}/cloud-functions/${fn}.zip"
done
```

## Commands

**Project root** ([`projects/`](projects/)):

```bash
terraform -chdir=infra/gcp/projects fmt -recursive
terraform -chdir=infra/gcp/projects init -backend=false    # local validate only
terraform -chdir=infra/gcp/projects validate
terraform -chdir=infra/gcp/projects plan -var-file=dev.terraform.tfvars
```

**Workload root** (`infra/gcp/workload/`):

```bash
cd infra/gcp/workload
terraform fmt -recursive
terraform init -backend=false    # local testing without GCS backend
terraform validate
terraform plan -var-file=dev.terraform.tfvars
```

Terraform automatically loads a file named `terraform.tfvars` if present. If you use `dev.terraform.tfvars`, avoid duplicating keys in `terraform.tfvars` or remove/rename `terraform.tfvars` so variables are not merged unexpectedly.

**Admin bootstrap** ([`admin/`](admin/)):

```bash
terraform -chdir=infra/gcp/admin fmt
terraform -chdir=infra/gcp/admin init -backend=false
terraform -chdir=infra/gcp/admin validate
terraform -chdir=infra/gcp/admin plan -var-file=terraform.tfvars
```

## Known limitations

- **Frontend without `frontend_domain`**: the load balancer serves **HTTP only** on the reserved global IP (no managed cert on bare IP). With `frontend_domain` set, managed SSL + HTTPS (and HTTP→HTTPS redirect) are provisioned. This differs from AWS CloudFront, which always offers HTTPS on `*.cloudfront.net`.
- **Optional resource labels**: root variable `labels` (map) is merged into default labels `app` and `env` and applied to supported resources (GCS buckets, Memorystore, Cloud Functions, Eventarc). Subnets/VPC do not set `labels` in Terraform for this provider version. The standalone [`bastion/`](bastion/) module accepts optional `labels` in its own `terraform.tfvars`.

## Notes

- **Managed SSL / custom domain**: set `frontend_domain` to enable managed certificate + HTTPS. Leave empty for HTTP-on-IP (dev/lab).
- **SPA routing**: the frontend URL map uses `default_custom_error_response_policy` on [`workload/modules/frontend/main.tf`](workload/modules/frontend/main.tf) so 403/404 from the GCS backend are served as `index.html` with HTTP 200, matching AWS CloudFront `CustomErrorResponses` and Vue Router deep links. The GCS bucket also sets `website { main_page_suffix = "index.html" }` for direct bucket semantics parity with S3 website hosting.
- **OpenAPI / API Gateway**: [`workload/modules/backend/gateway/openapi.yaml.tftpl`](workload/modules/backend/gateway/openapi.yaml.tftpl) is rendered with function URLs and JWT issuer settings (Identity Platform / securetoken). **CORS** response headers are set in Cloud Function Python code; OPTIONS is routed to the same backends as other methods.
- **Bastion**: requires the **network** stack applied first; pass `subnet_self_link` from `module.network.subnet_self_link`. Network stack opens IAP TCP forwarding to VMs tagged `bastion`. **Operators** who run `gcloud compute ssh --tunnel-through-iap` need **`roles/iap.tunnelResourceAccessor`** on the project or instance (the bastion VM service account does not grant this to humans).
- **OIDC / GitHub Actions**: [`oidc/main.tf`](oidc/main.tf) creates one shared WIF pool/provider in the **admin** project and **one deploy + one tests service account per environment key** in `env_projects`. Deploy SAs get roles aligned with Terraform resources (including Cloud Functions Gen2 / Run IAM and API Gateway). Tests SAs get least-privilege roles for IAP bastion SSH, Memorystore/Secret Manager, GCS config object CRUD, Identity Platform user lifecycle, API Gateway visibility, and API keys read—not project-wide `roles/viewer`. Restrict GitHub tokens with `attribute_condition` in [`oidc/terraform.tfvars`](oidc/terraform.tfvars.example). Ensure `serviceusage.googleapis.com` is usable on the admin project before OIDC Terraform manages other API enablements there.

## CI

Use `terraform fmt -check` and `terraform validate` in pipelines (with `-backend=false` or a test backend config as appropriate).

## Migrating workload remote state to `env/<env>/workload`

If you previously used the GCS prefix `env/dev/` (without a `workload/` segment) for the workload root **when that root lived at `infra/gcp/`**, copy the state to `env/dev/workload` before using this layout. **`terraform apply` and `terraform destroy` are not required for migration**; use `terraform init` and `terraform plan` only.

From a checkout **before** this restructure (workload at `infra/gcp/`):

```bash
cd infra/gcp

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/dev/"

terraform init -migrate-state \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/dev/workload"

terraform plan -var-file=dev.terraform.tfvars
# Expect: no changes.

# Optional: remove old object after plan is clean:
# gcloud storage rm "gs://${STATE_BUCKET}/env/dev/default.tfstate"
```

Then switch to this repo layout, move local `dev.terraform.tfvars` (and `.terraform/` if you rely on it) into `infra/gcp/workload/`, and re-init:

```bash
cd infra/gcp/workload

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/dev/workload"

terraform plan -var-file=dev.terraform.tfvars
# Expect: no changes again.
```
