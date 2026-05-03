output "primary_endpoint" {
  description = "Memorystore primary endpoint host:port"
  value       = "${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
}

output "primary_endpoint_host" {
  value = google_redis_instance.cache.host
}

output "memorystore_port" {
  description = "TCP port Memorystore exposes for the primary endpoint (API-assigned; typically 6379)."
  value       = google_redis_instance.cache.port
}

output "reader_endpoint" {
  description = "Memorystore read endpoint host:port (Standard HA)."
  value       = "${google_redis_instance.cache.read_endpoint}:${google_redis_instance.cache.port}"
}

output "memorystore_auth_secret_id" {
  description = "Secret Manager secret id for Memorystore AUTH (short id)."
  value       = google_secret_manager_secret.memorystore_auth.secret_id
}

output "auth_secret_resource_name" {
  value     = google_secret_manager_secret.memorystore_auth.id
  sensitive = true
}
