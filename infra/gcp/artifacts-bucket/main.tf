provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_project_service" "storage" {
  project            = var.project_id
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

resource "google_storage_bucket" "artifacts" {
  project                     = var.project_id
  name                        = "${var.bucket_name}-${var.project_number}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = local.allow_force_destroy

  versioning {
    enabled = true
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_age_days > 0 ? [1] : []
    content {
      action {
        type = "Delete"
      }
      condition {
        days_since_noncurrent_time = var.lifecycle_age_days
        with_state                 = "ARCHIVED"
      }
    }
  }

  depends_on = [google_project_service.storage]
}
