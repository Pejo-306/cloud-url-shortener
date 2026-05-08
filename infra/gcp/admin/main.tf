resource "google_project" "this" {
  name            = var.admin_project_id
  project_id      = var.admin_project_id
  org_id          = var.org_id
  billing_account = var.billing_account
}

resource "google_project_service" "apis" {
  for_each = local.admin_services

  project            = google_project.this.project_id
  service            = each.key
  disable_on_destroy = false

  depends_on = [google_project.this]
}

resource "google_storage_bucket" "terraform_state" {
  project                     = google_project.this.project_id
  name                        = "${var.state_bucket_name}-${google_project.this.number}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.allow_force_destroy

  versioning {
    enabled = true
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_age_days_state > 0 ? [1] : []
    content {
      action {
        type = "Delete"
      }
      condition {
        days_since_noncurrent_time = var.lifecycle_age_days_state
        with_state                 = "ARCHIVED"
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_storage_bucket" "artifacts" {
  project                     = google_project.this.project_id
  name                        = "${var.artifacts_bucket_name}-${google_project.this.number}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = var.allow_force_destroy

  versioning {
    enabled = true
  }

  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_age_days_artifacts > 0 ? [1] : []
    content {
      action {
        type = "Delete"
      }
      condition {
        days_since_noncurrent_time = var.lifecycle_age_days_artifacts
        with_state                 = "ARCHIVED"
      }
    }
  }

  depends_on = [google_project_service.apis]
}
