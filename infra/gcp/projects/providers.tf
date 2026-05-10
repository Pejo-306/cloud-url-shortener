# Client-side APIs (e.g. identitytoolkit, apikeys) need a quota project to bill us by API usage.
# We can set a quota project on ADC, but the Terraform GCP provider does not read it (well-known issue).
# 
# To circumvent this, we force the provider to pass quota project via the properties
# `billing_project` and `user_project_override`. But we only do this for identity
# platform resources. Otherwise we'd have absolutely every resource needlessly
# require their APIs enabled on the quota project.
# 
# This however introduces a circular dependency - we need the service API
# `serviceusage.googleapis.com` enabled so Terraform's GCP provider can fetch the quota project.
# Since this happens BEFORE we get to enable our list of used GCP APIs, this means
# we can't use Terraform to enable the API for us. We need a manual bootstrap step
# after the project is created:
#
# ```bash
# gcloud services enable serviceusage.googleapis.com --project=cloudshortener-dev
# ```
#
# If you didn't understand anything, ask claude to explain this. It's a weird
# chicken-and-egg problem.

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

provider "google" {
  alias                 = "with_quota_project"
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
