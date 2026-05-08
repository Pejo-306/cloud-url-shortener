# Remote state: shared bucket, per-environment prefix.
# Bootstrap first: terraform -chdir=../admin init && apply
# Then: terraform init -backend-config="bucket=YOUR_BUCKET" -backend-config="prefix=env/dev/workload"
terraform {
  backend "gcs" {
    # Overridden via -backend-config (bucket name + prefix per env)
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "env/local/workload-placeholder"
  }
}
