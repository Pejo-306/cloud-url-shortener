# Client-side APIs (e.g. identitytoolkit, apikeys) need a quota project to bill us by API usage.
# We can set a quota project on ADC, but the Terraform GCP provider does not read it (well-known issue).
# 
# To circumvent this, we force the provider to pass quota project via the properties
# `billing_project` and `user_project_override`.
# 
# This however introduces a circular depency - we need the service API
# `serviceusage.googleapis.com` enabled so Terraform's GCP provider can fetch the quota project.
# Since this happens BEFORE we get to enable our list of used GCP APIs, this means
# we can't use Terraform to enable the API for us. We need a manual bootstrap step
# after the project is created:
#
# ```bash
# gcloud services enable serviceusage.googleapis.com --project=cloudshortener-dev
# ```

provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
