locals {
  pool_id = var.pool_id != "" ? var.pool_id : "gh${substr(sha256(var.app_name), 0, 6)}"

  repo_attr = "${var.github_org}/${var.github_repo}"

  admin_required_services = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "sts.googleapis.com",
  ])

  env_required_services = toset([
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
  ])

  deploy_roles = toset([
    "roles/cloudfunctions.admin",
    "roles/apigateway.admin",
    "roles/storage.admin",
    "roles/redis.admin",
    "roles/compute.networkAdmin",
    "roles/compute.securityAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/secretmanager.admin",
    "roles/identityplatform.admin",
    "roles/eventarc.admin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/serviceusage.apiKeysAdmin",
    "roles/vpcaccess.admin",
    "roles/compute.instanceAdmin.v1",
  ])

  tests_roles = toset([
    "roles/compute.instanceAdmin.v1",
    "roles/iam.serviceAccountUser",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectUser",
    "roles/iap.tunnelResourceAccessor",
    "roles/firebaseauth.admin",
    "roles/apigateway.viewer",
    "roles/redis.viewer",
    "roles/serviceusage.apiKeysViewer",
  ])

  # Flatten env x API/role combinations into stable maps for `for_each`.
  # This lets Terraform create one resource per environment-specific grant while
  # keeping enough context to target the right project and service account.
  #
  # Example deploy_bindings entry:
  # "dev__roles__storage.admin" = {
  #   project_id = "cloudshortener-dev",
  #   role = "roles/storage.admin",
  #   env_key = "dev"
  # }
  env_api_instances = merge([
    for env_key, env in var.env_projects : {
      for svc in local.env_required_services :
      "${env_key}__${replace(svc, ".", "_")}" => {
        project_id = env.project_id
        service    = svc
      }
    }
  ]...)

  deploy_bindings = merge([
    for env_key, env in var.env_projects : {
      for role in local.deploy_roles :
      "${env_key}__${replace(role, "/", "__")}" => {
        project_id = env.project_id
        role       = role
        env_key    = env_key
      }
    }
  ]...)

  tests_bindings = merge([
    for env_key, env in var.env_projects : {
      for role in local.tests_roles :
      "${env_key}__${replace(role, "/", "__")}" => {
        project_id = env.project_id
        role       = role
        env_key    = env_key
      }
    }
  ]...)
}
