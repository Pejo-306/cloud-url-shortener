resource "google_service_account" "functions" {
  project      = var.project_id
  account_id   = "cf-functions-${var.app_env}"
  display_name = "Cloud Functions (${var.app_env})"

  depends_on = [google_project_service.apis]
}

# API Gateway uses this SA to mint OIDC ID tokens for outbound backend calls to
# Cloud Run (Cloud Functions Gen2). Wired into our API config. Without an explicit
# SA, the gateway falls back to the default Compute SA, which is not the principal
# which we want to allow invoking our functions
resource "google_service_account" "api_gateway_runtime" {
  project      = var.project_id
  account_id   = "api-gateway-${var.app_env}"
  display_name = "API Gateway runtime (${var.app_env})"

  depends_on = [google_project_service.apis]
}

resource "google_service_account" "eventarc_trigger" {
  project      = var.project_id
  account_id   = "cf-eventarc-trigger-${var.app_env}"
  display_name = "Eventarc trigger for config warming (${var.app_env})"

  depends_on = [google_project_service.apis]
}

resource "google_project_iam_member" "functions_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.functions.email}"

  depends_on = [google_service_account.functions]
}

resource "google_project_iam_member" "eventarc_trigger_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_trigger.email}"

  depends_on = [google_service_account.eventarc_trigger]
}

# Cloud Functions (now) uses the default Compute SA, which doesn't have necessary
# permissions to build cloud functions. This binding gives those permissions.
resource "google_project_iam_member" "default_compute_sa_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${local.default_compute_email}"

  depends_on = [google_project_service.apis]
}

# Ensure Eventarc's Google-managed service account has roles/eventarc.serviceAgent on this
# project before creating triggers. Otherwise the first apply can race API enable vs. IAM
# propagation and fail with "Permission denied while using the Eventarc Service Agent".
# https://github.com/hashicorp/terraform-provider-google/issues/14584
resource "google_project_iam_member" "eventarc_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:${local.eventarc_agent_email}"

  depends_on = [google_project_service.apis]
}

# When Eventarc creates a GCS trigger, it sets up a Pub/Sub topic and GCS notification.
# The Cloud Storage service agent needs permissions to publish notifications to that
# Pub/Sub topic. See https://cloud.google.com/eventarc/docs/run/quickstart-storage#before-you-begin
resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${local.gcs_agent_email}"

  depends_on = [google_project_service.apis]
}
