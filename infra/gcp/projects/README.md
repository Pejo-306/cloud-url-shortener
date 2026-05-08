# GCP Project Root

Reusable Terraform root for one CloudShortener environment project (`dev`, `staging`, `prod`). Use a separate tfvars file and a separate backend prefix per environment. The shared GCS state bucket is created by [`../admin/`](../admin/); set `STATE_BUCKET` from `terraform output -raw state_bucket_name` there before `init` here.

Manages long-lived project prerequisites: service APIs, Identity Platform, browser API key, custom service accounts, project-level IAM, and Secret Manager secret shells. Operators still seed secret values separately.

```bash
terraform -chdir=infra/gcp/projects init -reconfigure \
  -backend-config="bucket=$STATE_BUCKET" \
  -backend-config="prefix=env/dev/project"

terraform -chdir=infra/gcp/projects plan -var-file=dev.terraform.tfvars
```

Repeat with `env/staging/project` + e.g. `staging.terraform.tfvars`, and `env/prod/project` + `prod.terraform.tfvars` 

Set at least:

```hcl
app_env        = "dev"
project_id     = "cloudshortener-dev"
project_number = "123456789012" # leave empty only when create_project = true
```

If `create_project = true` and `billing_account` is set, bootstrap Cloud Billing
before the first apply:

```bash
gcloud services enable cloudbilling.googleapis.com --project=cloudshortener-dev
```

For a brand-new project, also bootstrap Service Usage before the provider uses
the project as a quota project:

```bash
gcloud services enable serviceusage.googleapis.com --project=cloudshortener-dev
```

Do not run `terraform apply` or `terraform destroy` unless you explicitly intend to change project-level resources.
