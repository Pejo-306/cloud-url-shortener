# Remote state: shared bucket, per-environment prefix.
# Bootstrap the bucket first: terraform -chdir=state-bucket init && apply
# Then: terraform init -backend-config="bucket=YOUR_BUCKET" -backend-config="prefix=env/dev"
terraform {
  backend "gcs" {
    # Overridden via -backend-config (bucket name + prefix per env)
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "env/local/root-placeholder"
  }
}
