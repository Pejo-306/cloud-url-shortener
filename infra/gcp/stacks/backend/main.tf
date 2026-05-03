resource "google_service_account" "functions" {
  project      = var.project_id
  account_id   = "cf-functions-${var.app_env}"
  display_name = "Cloud Functions (${var.app_env})"
}

# API Gateway uses this SA to mint OIDC ID tokens for outbound backend calls to
# Cloud Run (Cloud Functions Gen2). Wired into our API config. Without an explicit
# SA, the gateway falls back to the default Compute SA, which is not the principal
# which we want to allow invoking our functions
resource "google_service_account" "api_gateway_runtime" {
  project      = var.project_id
  account_id   = "api-gateway-${var.app_env}"
  display_name = "API Gateway runtime (${var.app_env})"
}

resource "google_project_iam_member" "functions_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_storage_bucket_iam_member" "functions_config_reader" {
  bucket = var.config_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.functions.email}"
}

# These 2 IAM bindings allow Cloud Functions to fetch function zips from the artifacts bucket
resource "google_storage_bucket_iam_member" "gcf_agent_artifacts_reader" {
  bucket = var.artifacts_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${var.project_number}@gcf-admin-robot.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "cloudbuild_agent_artifacts_reader" {
  bucket = var.artifacts_bucket
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:service-${var.project_number}@gcp-sa-cloudbuild.iam.gserviceaccount.com"
}

# Cloud Functions (now) uses the default Compute SA, which doesn't have necessary
# permissions to build cloud functions. This binding gives those permissions.
resource "google_project_iam_member" "default_compute_sa_builder" {
  project = var.project_id
  role    = "roles/cloudbuild.builds.builder"
  member  = "serviceAccount:${var.project_number}-compute@developer.gserviceaccount.com"
}

# Ensure Eventarc's Google-managed service account has roles/eventarc.serviceAgent on this
# project before creating triggers. Otherwise the first apply can race API enable vs. IAM
# propagation and fail with "Permission denied while using the Eventarc Service Agent".
# https://github.com/hashicorp/terraform-provider-google/issues/14584
resource "google_project_iam_member" "eventarc_google_managed_service_agent" {
  project = var.project_id
  role    = "roles/eventarc.serviceAgent"
  member  = "serviceAccount:service-${var.project_number}@gcp-sa-eventarc.iam.gserviceaccount.com"
}

# When Eventarc creates a GCS trigger, it sets up a Pub/Sub topic and GCS notification.
# The Cloud Storage service agent needs permissions to publish notifications to that
# Pub/Sub topic. See https://cloud.google.com/eventarc/docs/run/quickstart-storage#before-you-begin
resource "google_project_iam_member" "gcs_agent_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${var.project_number}@gs-project-accounts.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "functions_memorystore_auth" {
  project   = var.project_id
  secret_id = var.memorystore_auth_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.functions.email}"
}

resource "google_cloudfunctions2_function" "shorten" {
  name     = "${var.app_name}-${var.app_env}-cf-shorten"
  project  = var.project_id
  location = var.region
  labels   = var.labels

  build_config {
    runtime     = var.function_runtime
    entry_point = var.shorten_runtime_entry_point
    source {
      storage_source {
        bucket = var.artifacts_bucket
        object = local.fn_source_object_shorten
      }
    }
  }

  service_config {
    max_instance_count             = 20
    min_instance_count             = 0
    available_memory               = "512M"
    timeout_seconds                = 30
    service_account_email          = google_service_account.functions.email
    all_traffic_on_latest_revision = true
    vpc_connector                  = local.vpc_connector
    vpc_connector_egress_settings  = "PRIVATE_RANGES_ONLY"
    ingress_settings               = "ALLOW_ALL"

    environment_variables = local.fn_env
  }

  depends_on = [
    google_storage_bucket_iam_member.gcf_agent_artifacts_reader,
    google_storage_bucket_iam_member.cloudbuild_agent_artifacts_reader,
  ]
}

resource "google_cloudfunctions2_function" "redirect" {
  name     = "${var.app_name}-${var.app_env}-cf-redirect"
  project  = var.project_id
  location = var.region
  labels   = var.labels

  build_config {
    runtime     = var.function_runtime
    entry_point = var.redirect_runtime_entry_point
    source {
      storage_source {
        bucket = var.artifacts_bucket
        object = local.fn_source_object_redirect
      }
    }
  }

  service_config {
    max_instance_count             = 50
    min_instance_count             = 0
    available_memory               = "256M"
    timeout_seconds                = 30
    service_account_email          = google_service_account.functions.email
    all_traffic_on_latest_revision = true
    vpc_connector                  = local.vpc_connector
    vpc_connector_egress_settings  = "PRIVATE_RANGES_ONLY"
    ingress_settings               = "ALLOW_ALL"

    environment_variables = local.fn_env
  }

  depends_on = [
    google_storage_bucket_iam_member.gcf_agent_artifacts_reader,
    google_storage_bucket_iam_member.cloudbuild_agent_artifacts_reader,
  ]
}

resource "google_cloudfunctions2_function" "warm" {
  name     = "${var.app_name}-${var.app_env}-cf-warm-config"
  project  = var.project_id
  location = var.region
  labels   = var.labels

  build_config {
    runtime     = var.function_runtime
    entry_point = var.warm_runtime_entry_point
    source {
      storage_source {
        bucket = var.artifacts_bucket
        object = local.fn_source_object_warm
      }
    }
  }

  service_config {
    max_instance_count             = 2
    min_instance_count             = 0
    available_memory               = "256M"
    timeout_seconds                = 120
    service_account_email          = google_service_account.functions.email
    all_traffic_on_latest_revision = true
    vpc_connector                  = local.vpc_connector
    vpc_connector_egress_settings  = "PRIVATE_RANGES_ONLY"
    ingress_settings               = "ALLOW_ALL" # Eventarc invokes this function; keep ingress open to Google eventing paths.

    environment_variables = local.fn_env
  }

  depends_on = [
    google_storage_bucket_iam_member.gcf_agent_artifacts_reader,
    google_storage_bucket_iam_member.cloudbuild_agent_artifacts_reader,
  ]
}

# API Gateway signs outbound calls to our Cloud Functions backends with the SA
# configured in our API config. Cloud Run checks if that SA has `roles/run.invoker`
# on the Gen2 function's underlying service. Without these 2 IAM bindings, Cloud Run
# would deny API gateway's requests with a `403`.
resource "google_cloud_run_v2_service_iam_member" "shorten_apigw_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.shorten.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_gateway_runtime.email}"
}

resource "google_cloud_run_v2_service_iam_member" "redirect_apigw_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.redirect.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.api_gateway_runtime.email}"
}

resource "google_service_account" "eventarc_trigger" {
  project      = var.project_id
  account_id   = "cf-eventarc-trigger-${var.app_env}"
  display_name = "Eventarc trigger for config warming (${var.app_env})"
}

resource "google_project_iam_member" "eventarc_trigger_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

resource "google_cloudfunctions2_function_iam_member" "warm_eventarc_invoker" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.warm.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

# Eventarc needs permissions to invoke Gen2 functions on Cloud Run
resource "google_cloud_run_v2_service_iam_member" "warm_eventarc_run_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.warm.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

resource "google_eventarc_trigger" "config_finalized" {
  project  = var.project_id
  name     = "${var.app_name}-${var.app_env}-config-finalized"
  location = var.region
  labels   = var.labels

  service_account = google_service_account.eventarc_trigger.email

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = var.config_bucket_name
  }

  destination {
    cloud_run_service {
      region  = var.region
      service = google_cloudfunctions2_function.warm.name
    }
  }

  depends_on = [
    google_cloudfunctions2_function_iam_member.warm_eventarc_invoker,
    google_cloud_run_v2_service_iam_member.warm_eventarc_run_invoker,
    google_project_iam_member.eventarc_trigger_receiver,
    google_project_iam_member.eventarc_google_managed_service_agent,
    google_project_iam_member.gcs_agent_pubsub_publisher,
  ]
}

resource "google_api_gateway_api" "api" {
  provider = google-beta
  project  = var.project_id
  api_id   = "${var.app_name}-${var.app_env}-api"
}

resource "google_api_gateway_api_config" "primary" {
  provider = google-beta
  project  = var.project_id

  api           = google_api_gateway_api.api.api_id
  api_config_id = local.api_config_id

  openapi_documents {
    document {
      path     = "openapi.yaml"
      contents = base64encode(local.openapi_yaml)
    }
  }

  gateway_config {
    backend_config {
      google_service_account = google_service_account.api_gateway_runtime.email
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_api_gateway_gateway" "gateway" {
  provider = google-beta
  project  = var.project_id
  region   = var.region

  api_config = google_api_gateway_api_config.primary.id
  gateway_id = "${var.app_name}-${var.app_env}-gw"

  depends_on = [
    google_api_gateway_api_config.primary,
    google_service_account.api_gateway_runtime,
    google_cloud_run_v2_service_iam_member.shorten_apigw_invoker,
    google_cloud_run_v2_service_iam_member.redirect_apigw_invoker,
  ]
}
