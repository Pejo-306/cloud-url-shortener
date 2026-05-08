output "frontend_bucket_name" {
  description = "GCS bucket hosting static frontend assets."
  value       = google_storage_bucket.frontend.name
}

output "frontend_url" {
  description = "Site URL (HTTPS if frontend domain is provided; else HTTP by IP)."
  value       = local.use_custom_domain ? "https://${var.frontend_domain}" : "http://${google_compute_global_address.lb_ip.address}"
}

output "load_balancer_ip" {
  description = "Global external IP for the frontend load balancer."
  value       = google_compute_global_address.lb_ip.address
}

output "cdn_backend_bucket_name" {
  description = "CDN-enabled backend to the GCS bucket."
  value       = google_compute_backend_bucket.cdn_lb_backend.name
}
