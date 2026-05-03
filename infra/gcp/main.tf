module "network" {
  source = "./stacks/network"

  project_id  = var.project_id
  app_name    = var.app_name
  app_env     = var.app_env
  region      = var.region
  subnet_cidr = var.subnet_cidr

  depends_on = [google_project_service.apis]
}

module "identity_platform" {
  source = "./stacks/identity-platform"

  project_id = var.project_id
  app_name   = var.app_name
  app_env    = var.app_env

  depends_on = [google_project_service.apis]
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

  depends_on = [module.network, google_project_service.apis]
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

  depends_on = [google_project_service.apis]
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

  depends_on = [google_project_service.apis]
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
  memorystore_auth_secret_id   = module.memorystore.memorystore_auth_secret_id
  identity_platform_project_id = module.identity_platform.project_id
  jwt_issuer                   = module.identity_platform.jwt_issuer
  jwt_jwks_uri                 = module.identity_platform.jwks_uri
  artifacts_bucket             = var.artifacts_bucket
  labels                       = local.resource_labels

  depends_on = [
    module.network,
    module.memorystore,
    module.config,
    module.identity_platform,
    google_project_service.apis,
  ]
}
