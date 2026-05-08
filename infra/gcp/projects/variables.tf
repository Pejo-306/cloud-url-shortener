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

variable "project_id" {
  type        = string
  description = "GCP project ID to deploy into (must exist unless create_project is true)."
}

# When `create_project` is `true`, leave `project_number` empty. Terraform templates
# will use the project number from the newly created project.
# When `create_project` is `false`, set `project_number` from:
#
# ```bash
# gcloud projects describe PROJECT_ID --format='value(projectNumber)'
# ```
variable "project_number" {
  type        = string
  description = "Numeric GCP project number."
  default     = ""

  validation {
    condition     = var.project_number == "" || can(regex("^[0-9]+$", var.project_number))
    error_message = "project_number must be empty or a numeric string."
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

variable "browser_api_key_generation" {
  type        = string
  description = "Bump to rotate the browser API key name suffix after GCP soft-delete collisions."
  default     = "v1"
}

variable "labels" {
  type        = map(string)
  description = "Optional extra resource labels merged with app/env defaults."
  default     = {}
}
