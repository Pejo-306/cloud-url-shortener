data "google_secret_manager_secret_version" "redis_credentials" {
  project = var.project_id
  secret  = local.redis_cloud_credentials_secret_id
}

resource "google_storage_bucket" "config" {
  project                     = var.project_id
  name                        = "${var.app_name}-${var.app_env}-config-${var.project_number}"
  location                    = var.region
  uniform_bucket_level_access = true
  labels                      = var.labels

  versioning {
    enabled = true
  }

  force_destroy = local.allow_force_destroy
}

resource "google_storage_bucket_object" "backend_config" {
  name    = var.config_object_name
  bucket  = google_storage_bucket.config.name
  content = local.config_body

  content_type = "application/json"
}
