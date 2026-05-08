resource "google_storage_bucket_iam_member" "functions_config_reader" {
  bucket = var.config_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${var.functions_sa_email}"
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

resource "google_secret_manager_secret_iam_member" "functions_memorystore_auth" {
  project   = var.project_id
  secret_id = var.memorystore_auth_secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.functions_sa_email}"
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
    service_account_email          = var.functions_sa_email
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
    service_account_email          = var.functions_sa_email
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
    service_account_email          = var.functions_sa_email
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
  member   = "serviceAccount:${var.api_gateway_runtime_sa_email}"
}

resource "google_cloud_run_v2_service_iam_member" "redirect_apigw_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.redirect.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.api_gateway_runtime_sa_email}"
}

resource "google_cloudfunctions2_function_iam_member" "warm_eventarc_invoker" {
  project        = var.project_id
  location       = var.region
  cloud_function = google_cloudfunctions2_function.warm.name
  role           = "roles/cloudfunctions.invoker"
  member         = "serviceAccount:${var.eventarc_trigger_sa_email}"
}

# Eventarc needs permissions to invoke Gen2 functions on Cloud Run
resource "google_cloud_run_v2_service_iam_member" "warm_eventarc_run_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.warm.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${var.eventarc_trigger_sa_email}"
}

resource "google_eventarc_trigger" "config_finalized" {
  project  = var.project_id
  name     = "${var.app_name}-${var.app_env}-config-finalized"
  location = var.region
  labels   = var.labels

  service_account = var.eventarc_trigger_sa_email

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
      google_service_account = var.api_gateway_runtime_sa_email
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
    google_cloud_run_v2_service_iam_member.shorten_apigw_invoker,
    google_cloud_run_v2_service_iam_member.redirect_apigw_invoker,
  ]
}
