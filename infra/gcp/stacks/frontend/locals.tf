locals {
  bucket_name         = lower(replace("${var.app_name}-${var.app_env}-frontend-${var.project_number}", "_", "-"))
  fe_prefix           = "${var.app_name}-${var.app_env}-fe"
  use_custom_domain   = var.frontend_domain != ""
  allow_force_destroy = var.app_env != "prod"
  # Load balancer data plane uses the Compute Engine service agent.
  lb_data_plane_sa = "serviceAccount:service-${var.project_number}@compute-system.iam.gserviceaccount.com"
}
