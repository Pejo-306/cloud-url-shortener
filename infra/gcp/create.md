1- Create state bucket

```bash
cd infra/gcp/state-bucket

cp terraform.tfvars.example terraform.tfvars
# Fill project_id, project_number, bucket_name, region.

terraform init
terraform apply -var-file=terraform.tfvars

export STATE_BUCKET="$(terraform output -raw bucket_name)"
```

2- Create artifacts bucket

```bash
cd ../artifacts-bucket

cp terraform.tfvars.example terraform.tfvars
# Fill project_id, project_number, bucket_name, region.

terraform init
terraform apply -var-file=terraform.tfvars

export ARTIFACTS_BUCKET="$(terraform output -raw bucket_name)"
```

Upload placeholder functions:

```bash
cd ../artifacts-bucket/placeholders/functions

for fn in shorten redirect warm; do
  (cd "$fn" && zip -r "../${fn}.zip" .)
  gcloud storage cp "${fn}.zip" \
    "gs://${ARTIFACTS_BUCKET}/${APP_ENV}/cloud-functions/${fn}.zip"
done
```

3- Project-level stack (APIs, Identity Platform, IAM SAs, secret shells)

Provision **before** the workload orchestrator. State prefix example: `env/${APP_ENV}/project`.

If Terraform manages the project itself (`create_project = true`) and sets
`billing_account`, bootstrap the Cloud Billing API before the first apply. This
is needed for Terraform to link or re-link the project to the billing account:

```bash
gcloud services enable cloudbilling.googleapis.com \
  --project="${ENV_PROJECT_ID}"
```

If this is a brand-new project, also bootstrap Service Usage before Terraform's
GCP provider uses the project as the quota project:

```bash
gcloud services enable serviceusage.googleapis.com \
  --project="${ENV_PROJECT_ID}"
```

```bash
cd infra/gcp/projects

cp terraform.tfvars.example dev.terraform.tfvars
# Set project_id, project_number (if project already exists), app_env, browser_api_key_generation, etc.

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/${APP_ENV}/project"

terraform apply -var-file=dev.terraform.tfvars
```

Copy SA emails and `memorystore_auth_secret_id` from `terraform output` into the workload tfvars (next step). The project root also creates the Redis Cloud credentials secret shell; seed its value in step 5.

4- Create OIDC stack

```bash
cd ../oidc

cp terraform.tfvars.example terraform.tfvars
# Fill admin_project_id, admin_project_number, env_projects, GitHub org/repo.

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=oidc/"

terraform apply -var-file=terraform.tfvars
```

If needed, undelete the WIF pool and providers + reimport into terraform:

```bash
gcloud iam workload-identity-pools describe github-oidc-provider \
  --project=cloudshortener-admin \
  --location=global

gcloud iam workload-identity-pools undelete github-oidc-provider \
  --project=cloudshortener-admin \
  --location=global

terraform import \
  'google_iam_workload_identity_pool.github' \
  'projects/cloudshortener-admin/locations/global/workloadIdentityPools/github-oidc-provider'

gcloud iam workload-identity-pools providers describe github \
  --project=cloudshortener-admin \
  --location=global \
  --workload-identity-pool=github-oidc-provider

gcloud iam workload-identity-pools providers undelete github \
  --project=cloudshortener-admin \
  --location=global \
  --workload-identity-pool=github-oidc-provider

terraform import \
  'google_iam_workload_identity_pool_provider.github' \
  'projects/cloudshortener-admin/locations/global/workloadIdentityPools/github-oidc-provider/providers/github'
```

5- Seed Redis Cloud secret value

```bash
export REDIS_USER="default"
export REDIS_PASS="your-redis-password"

export PROJECT_ID=cloudshortener-dev
export APP_NAME=cloudshortener
export APP_ENV=dev
export SECRET_NAME="${APP_NAME}-${APP_ENV}-secret-redis-credentials"

printf '{"username":"%s","password":"%s"}' "$REDIS_USER" "$REDIS_PASS" \
  | gcloud secrets versions add "$SECRET_NAME" \
      --project="$PROJECT_ID" \
      --data-file=-
```

6- Workload stack (network, Memorystore, config, frontend, backend)

State prefix example: `env/${APP_ENV}/workload` (separate from `.../project`).

```bash
cd infra/gcp/workload

cp terraform.tfvars.example dev.terraform.tfvars
# Fill project_id, project_number, redis_cloud_*, artifacts_bucket,
# and SA emails + memorystore_auth_secret_id from projects root outputs.

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/${APP_ENV}/workload"

terraform apply -var-file=dev.terraform.tfvars
```

**Note:** Terraform auto-loads any file named `terraform.tfvars` in this directory. If you use `dev.terraform.tfvars`, remove or rename a conflicting `terraform.tfvars` here so variables are not merged unexpectedly.

7- Create bastion

```bash
# get subnet self link from workload (after apply)
export APP_NAME="cloudshortener"
export APP_ENV="dev"
export REGION="europe-west1"

export SUBNET_SELF_LINK="$(
gcloud compute networks subnets describe "${APP_NAME}-${APP_ENV}-subnet" \
    --project="${ENV_PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(selfLink)'
)"
```

```bash
# apply bastion stack
cd infra/gcp/bastion

cp terraform.tfvars.example terraform.tfvars
# Fill project_id, app_name, app_env, region.
# You can pass subnet_self_link via CLI instead of storing it.

terraform init -reconfigure \
  -backend-config="bucket=${STATE_BUCKET}" \
  -backend-config="prefix=env/${APP_ENV}/bastion"

terraform apply \
  -var-file=terraform.tfvars \
  -var="subnet_self_link=${SUBNET_SELF_LINK}"
```

8- Verify by invoking cloud functions

From repo root (or set `-chdir` accordingly). API URL comes from the **workload** state; web API key from the **projects** state.

```bash
export API_BASE="$(terraform -chdir=infra/gcp/workload output -raw api_url)"
export WEB_API_KEY="$(
  terraform -chdir=infra/gcp/projects output -raw identity_web_api_key
)"

export TEST_EMAIL="curl-test-$(date +%s)@example.com"
export TEST_PASSWORD="abc123"
export TARGET_URL="https://example.com/some/long/url"

export ID_TOKEN="$(
  curl -sS \
    -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${WEB_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"${TEST_EMAIL}\",
      \"password\": \"${TEST_PASSWORD}\",
      \"returnSecureToken\": true
    }" \
  | jq -r '.idToken'
)"

# invoke POST /v1/shorten
curl -i \
  -X POST "${API_BASE}/v1/shorten" \
  -H "Authorization: Bearer ${ID_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"targetUrl\": \"${TARGET_URL}\"
  }"

# invoke GET /{shortcode}
curl -i -X GET "${API_BASE}/abc123"
```


9- Verify connectivity to bastion:

```bash
gcloud secrets versions access latest --project=cloudshortener-dev --secret=cloudshortener-dev-secret-memorystore-auth
gcloud compute ssh cloudshortener-dev-bastion --project=cloudshortener-dev --zone=europe-west1-b --tunnel-through-iap
redis-cli --tls --insecure -h 10.21.146.4 -p 6378 -a ecea0824-4c91-4b37-b508-ce367c032526
```