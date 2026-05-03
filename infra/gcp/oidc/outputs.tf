output "admin_project_id" {
  description = "Project hosting the shared Workload Identity pool and provider."
  value       = var.admin_project_id
}

output "admin_project_number" {
  description = "Numeric project number for the admin project (from tfvars)."
  value       = var.admin_project_number
}

output "workload_identity_pool_id" {
  value = google_iam_workload_identity_pool.github.workload_identity_pool_id
}

output "workload_identity_pool_name" {
  value = google_iam_workload_identity_pool.github.name
}

output "workload_identity_provider_name" {
  value = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account_emails" {
  description = "Deploy service account emails keyed by env_projects map key."
  value       = { for env, sa in google_service_account.deploy : env => sa.email }
}

output "tests_service_account_emails" {
  description = "Tests service account emails keyed by env_projects map key."
  value       = { for env, sa in google_service_account.tests : env => sa.email }
}

output "github_wif_provider_path" {
  description = "Value for GitHub Actions workload_identity_provider (projects/.../locations/global/workloadIdentityPools/.../providers/...)."
  value       = google_iam_workload_identity_pool_provider.github.name
}
