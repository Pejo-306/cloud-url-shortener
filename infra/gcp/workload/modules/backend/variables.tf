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

variable "log_level" {
  type    = string
  default = "INFO"
}

variable "vpc_connector_name" {
  type = string
}

variable "config_bucket_name" {
  type = string
}

variable "config_object_name" {
  type    = string
  default = "backend-config.json"
}

variable "memorystore_primary_host" {
  type        = string
  description = "Memorystore primary hostname (no port)."
}

variable "memorystore_port" {
  type    = number
  default = 6379
}

variable "memorystore_auth_secret_id" {
  type = string
}

variable "functions_sa_email" {
  type        = string
  description = "Service account email used by all Cloud Functions at runtime."
}

variable "api_gateway_runtime_sa_email" {
  type        = string
  description = "Service account email API Gateway uses to call the Cloud Functions backends."
}

variable "eventarc_trigger_sa_email" {
  type        = string
  description = "Service account email Eventarc uses to invoke the config warm function."
}

variable "identity_platform_project_id" {
  type        = string
  description = "GCP project id used as Firebase/Identity Platform JWT audience."
}

variable "jwt_issuer" {
  type = string
}

variable "jwt_jwks_uri" {
  type = string
}

variable "artifacts_bucket" {
  type        = string
  description = "GCS artifacts bucket with uploaded function source archives (.zip) under {app_env}/cloud-functions/."
}

# Cloud Functions entry point is a top-level Python callable which we define in main.py
# when we zip functions and upload to artifacts bucket.
variable "shorten_runtime_entry_point" {
  type        = string
  description = "Python entry point for shorten Cloud Function."
  default     = "shorten_url"
}

variable "redirect_runtime_entry_point" {
  type        = string
  description = "Python entry point for redirect Cloud Function."
  default     = "redirect_url"
}

variable "warm_runtime_entry_point" {
  type        = string
  description = "Python entry point for warm-config Cloud Function."
  default     = "warm_appconfig_cache"
}

variable "function_runtime" {
  type    = string
  default = "python313"
}

variable "labels" {
  type        = map(string)
  description = "Labels applied to Cloud Functions and Eventarc trigger."
  default     = {}
}
