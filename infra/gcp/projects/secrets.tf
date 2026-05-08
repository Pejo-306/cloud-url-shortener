resource "google_secret_manager_secret" "memorystore_auth" {
  project   = var.project_id
  secret_id = "${var.app_name}-${var.app_env}-secret-memorystore-auth"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "redis_cloud_credentials" {
  project   = var.project_id
  secret_id = "${var.app_name}-${var.app_env}-secret-redis-credentials"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}
