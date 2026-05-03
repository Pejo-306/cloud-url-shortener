variable "app_name" {
  type        = string
  description = "Application name (e.g. cloudshortener)."
  default     = "cloudshortener"

  validation {
    condition = (
      var.app_name == lower(var.app_name) &&
      length(var.app_name) >= 1 &&
      length(var.app_name) <= 40 &&
      can(regex("^([a-z]|[a-z][a-z0-9-]*[a-z0-9])$", var.app_name))
    )
    error_message = "app_name must be lowercase | 1-40 chars | start with a letter | end with a letter or digit | and contain only letters, digits, and hyphens."
  }
}

variable "app_env" {
  type        = string
  description = "Environment: local, dev, staging, prod."
  default     = "dev"

  validation {
    condition     = contains(["local", "dev", "staging", "prod"], var.app_env)
    error_message = "app_env must be one of: local, dev, staging, prod."
  }
}

variable "region" {
  type        = string
  description = "GCP region for regional resources."
  default     = "europe-west1"
}

variable "subnet_cidr" {
  type        = string
  description = "CIDR for the primary regional subnet (workloads + private endpoints)."
  default     = "10.0.1.0/24"

  validation {
    condition     = can(cidrhost(var.subnet_cidr, 0))
    error_message = "subnet_cidr must be a valid IPv4 CIDR block."
  }
}

variable "project_id" {
  type        = string
  description = "GCP project ID to deploy into (must exist unless create_project is true)."
}

variable "project_number" {
  type        = string
  description = "Numeric GCP project number."

  validation {
    condition     = can(regex("^[0-9]+$", var.project_number))
    error_message = "project_number must be a numeric string."
  }
}

variable "billing_account" {
  type        = string
  description = "Billing account ID (012345-6789AB-CDEF01). Required when create_project is true."
  default     = ""
}

variable "org_id" {
  type        = string
  description = "Optional organization ID for google_project (numeric). Use org_id or folder_id when create_project is true."
  default     = ""
}

variable "folder_id" {
  type        = string
  description = "Optional folder ID for google_project when create_project is true."
  default     = ""
}

variable "create_project" {
  type        = bool
  description = "If true, create google_project (requires billing_account and org_id/folder_id)."
  default     = false
}

variable "log_level" {
  type        = string
  description = "LOG_LEVEL for Cloud Functions."
  default     = "INFO"
}

variable "memorystore_port" {
  type        = number
  description = "TCP port to open on the VPC firewall for Redis clients. Documentation-only since MemoryStore doesn't allow configuring the Redis port."
  default     = 6379
}

variable "memorystore_memory_size_gb" {
  type        = number
  description = "Memorystore instance memory size (GB)."
  default     = 1
}

variable "memorystore_engine_version" {
  type        = string
  description = "Memorystore redis_version (e.g. REDIS_7_0)."
  default     = "REDIS_7_0"
}

variable "redis_cloud_host" {
  type        = string
  description = "Redis Cloud hostname for the primary datastore (baked into backend-config.json)."
  default     = ""
}

variable "redis_cloud_port" {
  type        = number
  description = "Redis Cloud TCP port."
  default     = 6379
}

variable "redis_cloud_db" {
  type        = number
  description = "Redis Cloud logical database index."
  default     = 0
}

variable "redis_cloud_credentials_secret" {
  type        = string
  description = "Secret with Redis Cloud credentials."
  default     = ""
}

variable "frontend_domain" {
  type        = string
  description = "FQDN for managed SSL certificate and HTTPS LB (e.g. app.example.com). Required for HTTPS frontend."
  default     = ""
}

variable "artifacts_bucket" {
  type        = string
  description = "GCS artifacts bucket containing Cloud Functions source zips under {app_env}/cloud-functions/."
  default     = ""
}

variable "browser_api_key_generation" {
  type        = string
  description = "Passed to identity-platform stack. Bump to rotate the browser API key name suffix after GCP soft-delete collisions."
  default     = "v1"
}

variable "labels" {
  type        = map(string)
  description = "Optional extra resource labels merged with app/env defaults."
  default     = {}
}
