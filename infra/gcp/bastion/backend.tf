terraform {
  backend "gcs" {
    bucket = "cloudshortener-tf-state-placeholder"
    prefix = "env/local/bastion-placeholder"
  }
}
