variable "admin_project_id" {
  type        = string
  description = "GCP project that hosts the shared GitHub Workload Identity pool and provider (admin project)."
}

variable "admin_project_number" {
  type        = string
  description = "Numeric project number for admin_project_id."

  validation {
    condition     = can(regex("^[0-9]+$", var.admin_project_number))
    error_message = "admin_project_number must be a numeric string."
  }
}

variable "env_projects" {
  type = map(object({
    project_id = string
  }))
  description = "Environment key (e.g. dev, prod) to workload project id."

  validation {
    condition     = length(var.env_projects) >= 1
    error_message = "env_projects must contain at least one environment."
  }
}

variable "app_name" {
  type        = string
  description = "Application name (e.g. cloudshortener)."

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

variable "github_org" {
  type        = string
  description = "GitHub organization or user (repository owner)."
}

variable "github_repo" {
  type = string
}

variable "pool_id" {
  type        = string
  description = "Workload Identity Pool ID (4-32 chars, start with letter). Leave empty for a deterministic hash from app_name."
  default     = ""
}

variable "attribute_condition" {
  type        = string
  description = "Optional CEL expression to restrict tokens (e.g. assertion.ref.startsWith('refs/heads/main'))."
  default     = ""
}

variable "enable_admin_project_apis" {
  type        = bool
  description = "Enable IAM/WIF-related APIs on admin_project_id. Disable if already managed elsewhere."
  default     = true
}

variable "enable_env_project_apis" {
  type        = bool
  description = "Enable minimal IAM APIs on each env project in env_projects. Usually false because infra/gcp/project.tf enables APIs on app projects."
  default     = false
}
