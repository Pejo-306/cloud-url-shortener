output "api_url" {
  description = "Public API Gateway base URL (include trailing path as needed)."
  value       = "https://${google_api_gateway_gateway.gateway.default_hostname}"
}

output "api_gateway_id" {
  value = google_api_gateway_gateway.gateway.gateway_id
}

output "shorten_function_name" {
  value = google_cloudfunctions2_function.shorten.name
}

output "redirect_function_name" {
  value = google_cloudfunctions2_function.redirect.name
}

output "warm_function_name" {
  value = google_cloudfunctions2_function.warm.name
}
