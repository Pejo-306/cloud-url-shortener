locals {
  bucket_name         = lower(replace("${var.app_name}-${var.app_env}-frontend-${var.project_number}", "_", "-"))
  fe_prefix           = "${var.app_name}-${var.app_env}-fe"
  use_custom_domain   = var.frontend_domain != ""
  allow_force_destroy = var.app_env != "prod"
  # Global external Application Load Balancers (EXTERNAL_MANAGED) require the
  # backend bucket to be publicly readable; they do not use a per-project
  # service account to fetch objects, unlike the classic EXTERNAL scheme.
  bucket_viewer_member = "allUsers"
}
