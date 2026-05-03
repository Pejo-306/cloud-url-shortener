resource "google_project" "this" {
  count = var.create_project ? 1 : 0

  name            = "${var.app_name}-${var.app_env}"
  project_id      = var.project_id
  org_id          = var.org_id != "" ? var.org_id : null
  folder_id       = var.folder_id != "" ? var.folder_id : null
  billing_account = var.billing_account

  lifecycle {
    prevent_destroy = true
  }
}

# We can't split this list of APIs into per-stack groups because Terraform doesn't
# allow multiple resources to own the enablement of the same API.
resource "google_project_service" "apis" {
  for_each = local.project_services

  project            = var.project_id
  service            = each.key
  disable_on_destroy = false

  depends_on = [google_project.this]
}
