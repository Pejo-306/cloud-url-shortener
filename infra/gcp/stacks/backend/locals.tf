locals {
  # GCS layout: gs://{bucket}/{app_env}/cloud-functions/{name}.zip (see infra/gcp/artifacts-bucket/)
  fn_source_prefix          = "${var.app_env}/cloud-functions"
  fn_source_object_shorten  = "${local.fn_source_prefix}/shorten.zip"
  fn_source_object_redirect = "${local.fn_source_prefix}/redirect.zip"
  fn_source_object_warm     = "${local.fn_source_prefix}/warm.zip"

  fn_env = {
    APP_ENV                 = var.app_env
    APP_NAME                = var.app_name
    LOG_LEVEL               = var.log_level
    GCP_PROJECT_ID          = var.project_id
    CONFIG_GCS_BUCKET       = var.config_bucket_name
    CONFIG_GCS_OBJECT       = var.config_object_name
    MEMORYSTORE_HOST        = var.memorystore_primary_host
    MEMORYSTORE_PORT        = tostring(var.memorystore_port)
    MEMORYSTORE_AUTH_SECRET = var.memorystore_auth_secret_id
  }

  vpc_connector = "projects/${var.project_id}/locations/${var.region}/connectors/${var.vpc_connector_name}"

  openapi_yaml = templatefile("${path.module}/gateway/openapi.yaml.tftpl", {
    api_title            = "API (${var.app_env})"
    jwt_issuer           = var.jwt_issuer
    jwt_jwks_uri         = var.jwt_jwks_uri
    jwt_audiences        = var.identity_platform_project_id
    shorten_backend_url  = google_cloudfunctions2_function.shorten.service_config[0].uri
    redirect_backend_url = google_cloudfunctions2_function.redirect.service_config[0].uri
  })

  api_config_id = "${var.app_env}-${substr(sha256("${local.openapi_yaml}|${var.api_gateway_runtime_sa_email}"), 0, 8)}"
}
