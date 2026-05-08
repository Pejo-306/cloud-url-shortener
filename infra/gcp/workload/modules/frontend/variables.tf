variable "project_id" {
  type = string
}

variable "project_number" {
  type        = string
  description = "Numeric GCP project number."
}

variable "region" {
  type        = string
  description = "GCS bucket location (regional, e.g. europe-west1)."
}

variable "app_name" {
  type = string
}

variable "app_env" {
  type = string
}

variable "frontend_domain" {
  type        = string
  description = "If non-empty, provision managed SSL cert and HTTPS forwarding rule."
  default     = ""
}

variable "labels" {
  type        = map(string)
  description = "Labels for the frontend GCS bucket."
  default     = {}
}
