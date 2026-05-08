output "config_bucket_name" {
  value = google_storage_bucket.config.name
}

output "config_object_name" {
  value = google_storage_bucket_object.backend_config.name
}

output "config_bucket_url" {
  value = "gs://${google_storage_bucket.config.name}/${google_storage_bucket_object.backend_config.name}"
}
