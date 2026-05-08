resource "google_compute_global_address" "memorystore_peering" {
  project       = var.project_id
  name          = "${var.app_name}-${var.app_env}-psa-memorystore-peering-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = var.peering_range_prefix_length
  network       = var.vpc_network_id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = var.vpc_network_id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.memorystore_peering.name]
}

resource "google_redis_instance" "cache" {
  project        = var.project_id
  name           = "${var.app_name}-${var.app_env}-memorystore"
  tier           = "STANDARD_HA"
  memory_size_gb = var.memory_size_gb
  region         = var.region

  redis_version      = var.memorystore_engine_version
  display_name       = "MemoryStore (${var.app_env})"
  reserved_ip_range  = google_compute_global_address.memorystore_peering.name
  labels             = var.labels
  authorized_network = var.vpc_network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"

  auth_enabled = true

  transit_encryption_mode = "SERVER_AUTHENTICATION"

  redis_configs = {
    maxmemory-policy = "volatile-lru"
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_secret_manager_secret_version" "memorystore_auth_version" {
  secret      = "projects/${var.project_id}/secrets/${var.memorystore_auth_secret_id}"
  secret_data = google_redis_instance.cache.auth_string

  depends_on = [google_redis_instance.cache]
}
