output "project_id" {
  description = "GCP project ID (Firebase/Identity Platform issuer segment)."
  value       = var.project_id
}

output "jwt_issuer" {
  description = "Issuer URL for JWT validation (e.g. API Gateway x-google-issuer)."
  value       = "https://securetoken.google.com/${var.project_id}"
}

output "jwks_uri" {
  description = "JWKS URI for Google securetoken."
  value       = "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com"
}

output "web_api_key" {
  description = "API key string for frontend Identity Platform / Firebase client config."
  value       = google_apikeys_key.browser.key_string
  sensitive   = true
}
