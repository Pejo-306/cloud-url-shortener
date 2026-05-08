locals {
  default_labels = {
    app = var.app_name
    env = var.app_env
  }
  resource_labels = merge(local.default_labels, var.labels)

  identity_platform_jwt_issuer   = "https://securetoken.google.com/${var.project_id}"
  identity_platform_jwt_jwks_uri = "https://www.googleapis.com/service_accounts/v1/metadata/x509/securetoken@system.gserviceaccount.com"
}
