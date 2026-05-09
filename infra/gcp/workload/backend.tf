# Initialize backend with prefix `env/dev/workload` inside the shared state bucket
terraform {
  backend "gcs" {
    # Overridden via -backend-config (bucket name + prefix per env)
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "env/local/workload-placeholder"
  }
}
