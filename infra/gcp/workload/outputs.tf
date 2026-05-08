output "api_url" {
  description = "Public API Gateway base URL."
  value       = module.backend.api_url
}

output "frontend_url" {
  description = "Public frontend URL."
  value       = module.frontend.frontend_url
}

output "frontend_bucket_name" {
  description = "GCS bucket that serves the frontend assets."
  value       = module.frontend.frontend_bucket_name
}

output "load_balancer_ip" {
  description = "External IP address of the frontend load balancer."
  value       = module.frontend.load_balancer_ip
}

output "config_bucket_name" {
  description = "GCS bucket that stores the backend configuration object."
  value       = module.config.config_bucket_name
}

output "memorystore_primary_endpoint" {
  description = "Primary Memorystore endpoint, including host and port."
  value       = module.memorystore.primary_endpoint
}

output "memorystore_reader_endpoint" {
  description = "Read-only Memorystore endpoint, including host and port."
  value       = module.memorystore.reader_endpoint
}

output "memorystore_port" {
  description = "Memorystore TCP port."
  value       = module.memorystore.memorystore_port
}

output "vpc_id" {
  description = "VPC network ID used by workload resources."
  value       = module.network.vpc_id
}

output "shorten_function_name" {
  description = "Name of the Cloud Function that creates short URLs."
  value       = module.backend.shorten_function_name
}

output "redirect_function_name" {
  description = "Name of the Cloud Function that redirects short URLs."
  value       = module.backend.redirect_function_name
}

output "warm_function_name" {
  description = "Name of the Cloud Function that warms backend configuration."
  value       = module.backend.warm_function_name
}
