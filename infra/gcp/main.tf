module "network" {
  source = "./stacks/network"

  project_id  = var.project_id
  app_name    = var.app_name
  app_env     = var.app_env
  region      = var.region
  subnet_cidr = var.subnet_cidr
}

module "memorystore" {
  source = "./stacks/memorystore"

  project_id                 = var.project_id
  app_name                   = var.app_name
  app_env                    = var.app_env
  region                     = var.region
  vpc_network_id             = module.network.vpc_id
  memory_size_gb             = var.memorystore_memory_size_gb
  memorystore_engine_version = var.memorystore_engine_version
  labels                     = local.resource_labels
  memorystore_auth_secret_id = var.memorystore_auth_secret_id

  depends_on = [module.network]
}

module "config" {
  source = "./stacks/config"

  project_id                     = var.project_id
  project_number                 = var.project_number
  app_name                       = var.app_name
  app_env                        = var.app_env
  region                         = var.region
  redis_cloud_host               = var.redis_cloud_host
  redis_cloud_port               = var.redis_cloud_port
  redis_cloud_db                 = var.redis_cloud_db
  redis_cloud_credentials_secret = var.redis_cloud_credentials_secret
  labels                         = local.resource_labels
}

module "frontend" {
  source = "./stacks/frontend"

  project_id      = var.project_id
  project_number  = var.project_number
  region          = var.region
  app_name        = var.app_name
  app_env         = var.app_env
  frontend_domain = var.frontend_domain
  labels          = local.resource_labels
}

module "backend" {
  source = "./stacks/backend"

  providers = {
    google      = google
    google-beta = google-beta
  }

  project_id                   = var.project_id
  project_number               = var.project_number
  app_name                     = var.app_name
  app_env                      = var.app_env
  region                       = var.region
  log_level                    = var.log_level
  vpc_connector_name           = module.network.vpc_connector_name
  config_bucket_name           = module.config.config_bucket_name
  config_object_name           = module.config.config_object_name
  memorystore_primary_host     = module.memorystore.primary_endpoint_host
  memorystore_port             = module.memorystore.memorystore_port
  memorystore_auth_secret_id   = var.memorystore_auth_secret_id
  identity_platform_project_id = var.project_id
  jwt_issuer                   = local.identity_platform_jwt_issuer
  jwt_jwks_uri                 = local.identity_platform_jwt_jwks_uri
  artifacts_bucket             = var.artifacts_bucket
  labels                       = local.resource_labels
  functions_sa_email           = var.functions_sa_email
  api_gateway_runtime_sa_email = var.api_gateway_runtime_sa_email
  eventarc_trigger_sa_email    = var.eventarc_trigger_sa_email

  depends_on = [
    module.network,
    module.memorystore,
    module.config,
  ]
}
