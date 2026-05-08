variable "project_id" {
  type = string
}

variable "app_name" {
  type = string
}

variable "app_env" {
  type = string
}

variable "region" {
  type = string
}

variable "vpc_network_id" {
  type        = string
  description = "VPC network id or self link for Memorystore authorized_network."
}

variable "memorystore_auth_secret_id" {
  type        = string
  description = "Secret Manager secret ID created by project root. Memorystore auth value is written here."
}

variable "memory_size_gb" {
  type    = number
  default = 1
}

variable "memorystore_engine_version" {
  type        = string
  description = "Redis version string e.g. REDIS_7_0."
  default     = "REDIS_7_0"
}

variable "peering_range_prefix_length" {
  type        = number
  description = "Peering range prefix length for Memorystore Private Service Access."
  default     = 24 # GCP API enforces at least a /24, even though we use it for a single STANDARD_HA instance
}

variable "labels" {
  type        = map(string)
  description = "Labels for Memorystore and related resources that support them."
  default     = {}
}
