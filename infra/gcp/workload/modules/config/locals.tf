locals {
  allow_force_destroy = var.app_env != "prod"

  redis_cloud_credentials_secret_id = (
    var.redis_cloud_credentials_secret != "" ?
    var.redis_cloud_credentials_secret :
    "${var.app_name}-${var.app_env}-secret-redis-credentials"
  )

  redis_credentials_raw = data.google_secret_manager_secret_version.redis_credentials.secret_data
  redis_credentials     = try(jsondecode(local.redis_credentials_raw), {})
  redis_username        = lookup(local.redis_credentials, "username", "")
  redis_password        = lookup(local.redis_credentials, "password", "")

  config_body = templatefile("${path.module}/files/backend-config.json.tftpl", {
    redis_host     = var.redis_cloud_host != "" ? var.redis_cloud_host : "pending-redis-cloud-host"
    redis_port     = var.redis_cloud_port
    redis_db       = var.redis_cloud_db
    redis_username = jsonencode(local.redis_username)
    redis_password = jsonencode(local.redis_password)
  })
}
