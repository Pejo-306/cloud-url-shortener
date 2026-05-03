output "bucket_name" {
  value = google_storage_bucket.terraform_state.name
}

output "bucket_url" {
  value = google_storage_bucket.terraform_state.url
}
