# Initialize backend with prefix `oidc/` inside the shared state bucket
terraform {
  backend "gcs" {
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "oidc"
  }
}
