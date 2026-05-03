variable "project_id" {
  type = string
}

variable "project_number" {
  type        = string
  description = "Numeric GCP project number."
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

variable "config_object_name" {
  type        = string
  description = "Object name for backend config JSON."
  default     = "backend-config.json"
}

variable "redis_cloud_host" {
  type        = string
  description = "Redis Cloud endpoint hostname (primary datastore)."
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

variable "labels" {
  type        = map(string)
  description = "Labels for the config GCS bucket."
  default     = {}
}
