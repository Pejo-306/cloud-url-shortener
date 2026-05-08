output "admin_project_id" {
  description = "Admin project ID."
  value       = google_project.this.project_id
}

output "admin_project_number" {
  description = "Numeric admin project number."
  value       = google_project.this.number
}

output "state_bucket_name" {
  value = google_storage_bucket.terraform_state.name
}

output "state_bucket_url" {
  value = google_storage_bucket.terraform_state.url
}

output "artifacts_bucket_name" {
  value = google_storage_bucket.artifacts.name
}

output "artifacts_bucket_url" {
  value = google_storage_bucket.artifacts.url
}
