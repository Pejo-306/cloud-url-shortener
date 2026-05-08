output "project_id" {
  description = "GCP project ID that hosts the workload infrastructure."
  value       = var.project_id
}

output "project_number" {
  description = "Numeric GCP project number used to address Google-managed service accounts."
  value       = local.effective_project_number
}

output "jwt_issuer" {
  description = "Identity Platform JWT issuer URL used by API Gateway."
  value       = "https://securetoken.google.com/${var.project_id}"
}

output "jwks_uri" {
  description = "Google Secure Token JWKS URI used to validate Identity Platform JWTs."
  value       = "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com"
}

output "identity_web_api_key" {
  description = "Browser API key used by the frontend Identity Platform / Firebase client."
  value       = google_apikeys_key.browser.key_string
  sensitive   = true
}

output "functions_sa_email" {
  description = "Service account email used by Cloud Functions at runtime."
  value       = google_service_account.functions.email
}

output "api_gateway_runtime_sa_email" {
  description = "Service account email API Gateway uses to call Cloud Functions."
  value       = google_service_account.api_gateway_runtime.email
}

output "eventarc_trigger_sa_email" {
  description = "Service account email Eventarc uses to invoke the config warm function."
  value       = google_service_account.eventarc_trigger.email
}

output "memorystore_auth_secret_id" {
  description = "Secret Manager secret ID where the workload root writes the Memorystore auth string."
  value       = google_secret_manager_secret.memorystore_auth.secret_id
}

output "redis_cloud_credentials_secret_id" {
  description = "Secret Manager secret ID where the operator seeds Redis Cloud credentials."
  value       = google_secret_manager_secret.redis_cloud_credentials.secret_id
}
