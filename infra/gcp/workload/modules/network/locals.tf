locals {
  vpc_access_connector_name = "${var.app_name}-${var.app_env}-conn"
}

check "vpc_connector_name_length" {
  assert {
    condition     = length(local.vpc_access_connector_name) <= 25
    error_message = "VPC Access connector name must be <= 25 characters (GCP). Shorten app_name or app_env."
  }
}
