output "api_url" {
  description = "HTTPS API Gateway base URL (cf. CloudFormation ApiUrl)."
  value       = module.backend.api_url
}

output "frontend_url" {
  description = "Frontend URL (HTTPS with custom domain or HTTP on LB IP)."
  value       = module.frontend.frontend_url
}

output "frontend_bucket_name" {
  value = module.frontend.frontend_bucket_name
}

output "load_balancer_ip" {
  value = module.frontend.load_balancer_ip
}

output "user_pool_project_id" {
  description = "Identity Platform / Firebase project id (cf. Cognito UserPoolId context)."
  value       = module.identity_platform.project_id
}

output "identity_web_api_key" {
  description = "Browser API key for Identity Platform client SDK."
  value       = module.identity_platform.web_api_key
  sensitive   = true
}

output "jwt_issuer" {
  value = module.identity_platform.jwt_issuer
}

output "config_bucket_name" {
  value = module.config.config_bucket_name
}

output "memorystore_primary_endpoint" {
  value = module.memorystore.primary_endpoint
}

output "memorystore_reader_endpoint" {
  value = module.memorystore.reader_endpoint
}

output "memorystore_port" {
  description = "Listener port returned by Memorystore for the primary endpoint."
  value       = module.memorystore.memorystore_port
}

output "vpc_id" {
  description = "VPC network id (cf. CloudFormation VpcId)."
  value       = module.network.vpc_id
}

output "memorystore_auth_secret_id" {
  value = module.memorystore.memorystore_auth_secret_id
}

output "shorten_function_name" {
  value = module.backend.shorten_function_name
}

output "redirect_function_name" {
  value = module.backend.redirect_function_name
}

output "warm_function_name" {
  value = module.backend.warm_function_name
}
