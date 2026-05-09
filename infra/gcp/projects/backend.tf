# Initialize backend with prefix `env/dev/` inside the shared state bucket
terraform {
  backend "gcs" {
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "env/local/project-placeholder"
  }
}
