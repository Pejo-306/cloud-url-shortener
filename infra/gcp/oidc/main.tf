provider "google" {
  project = var.admin_project_id
  region  = "global"
}

resource "google_project_service" "admin_apis" {
  for_each = var.enable_admin_project_apis ? local.admin_required_services : toset([])

  project            = var.admin_project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_project_service" "env_apis" {
  for_each = var.enable_env_project_apis ? local.env_api_instances : {}

  project            = each.value.project_id
  service            = each.value.service
  disable_on_destroy = false
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.admin_project_id
  workload_identity_pool_id = local.pool_id
  display_name              = "GitHub WIF pool (${var.app_name})"
  description               = "OIDC pool for GitHub Actions (repo ${local.repo_attr})."
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.admin_project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  # Default: allow only tokens from the configured GitHub repo.
  attribute_condition = var.attribute_condition != "" ? var.attribute_condition : "assertion.repository == \"${local.repo_attr}\""

  depends_on = [google_iam_workload_identity_pool.github]
}

resource "google_service_account" "deploy" {
  for_each = var.env_projects

  project      = each.value.project_id
  account_id   = "gh-deploy-${each.key}"
  display_name = "GitHub deploy SA (${each.key})"
}

resource "google_service_account" "tests" {
  for_each = var.env_projects

  project      = each.value.project_id
  account_id   = "gh-tests-${each.key}"
  display_name = "GitHub tests SA (${each.key})"
}

resource "google_service_account_iam_member" "deploy_wif" {
  for_each = var.env_projects

  service_account_id = google_service_account.deploy[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${local.repo_attr}"

  depends_on = [
    google_iam_workload_identity_pool_provider.github,
    google_service_account.deploy,
  ]
}

resource "google_service_account_iam_member" "tests_wif" {
  for_each = var.env_projects

  service_account_id = google_service_account.tests[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${local.repo_attr}"

  depends_on = [
    google_iam_workload_identity_pool_provider.github,
    google_service_account.tests,
  ]
}

resource "google_project_iam_member" "deploy_role_bindings" {
  for_each = local.deploy_bindings

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.deploy[each.value.env_key].email}"

  depends_on = [google_service_account.deploy]
}

resource "google_project_iam_member" "tests_role_bindings" {
  for_each = local.tests_bindings

  project = each.value.project_id
  role    = each.value.role
  member  = "serviceAccount:${google_service_account.tests[each.value.env_key].email}"

  depends_on = [google_service_account.tests]
}
