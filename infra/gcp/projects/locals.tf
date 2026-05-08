locals {
  default_labels = {
    app = var.app_name
    env = var.app_env
  }
  resource_labels = merge(local.default_labels, var.labels)

  project_services = toset([
    "apikeys.googleapis.com",
    "apigateway.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "eventarc.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "iap.googleapis.com",
    "identitytoolkit.googleapis.com",
    "pubsub.googleapis.com",
    "redis.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicecontrol.googleapis.com",
    "servicemanagement.googleapis.com",
    "servicenetworking.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
    "vpcaccess.googleapis.com",
  ])

  effective_project_number = length(google_project.this) > 0 ? tostring(google_project.this[0].number) : var.project_number

  eventarc_agent_email  = "service-${local.effective_project_number}@gcp-sa-eventarc.iam.gserviceaccount.com"
  gcs_agent_email       = "service-${local.effective_project_number}@gs-project-accounts.iam.gserviceaccount.com"
  default_compute_email = "${local.effective_project_number}-compute@developer.gserviceaccount.com"
}
