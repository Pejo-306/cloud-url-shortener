variable "project_id" {
  type        = string
  description = "Project that will own the Terraform state bucket (often an org admin / shared project)."
}

variable "project_number" {
  type        = string
  description = "Numeric GCP project number of the admin project."

  validation {
    condition     = can(regex("^[0-9]+$", var.project_number))
    error_message = "project_number must be a numeric string."
  }
}

variable "bucket_name" {
  type        = string
  description = "Base name for the GCS state bucket. The project number is appended automatically for global uniqueness."
}

variable "region" {
  type        = string
  description = "GCS bucket location."
  default     = "europe-west1"
}

variable "lifecycle_age_days" {
  type        = number
  description = "Delete non-current object versions older than this many days (0 = disable)."
  default     = 365
}
