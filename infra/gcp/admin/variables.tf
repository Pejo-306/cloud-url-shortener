variable "admin_project_id" {
  type        = string
  description = "Desired GCP project ID for the shared admin/bootstrap project."
}

variable "org_id" {
  type        = string
  description = "Organization ID (numeric) for google_project."

  validation {
    condition     = can(regex("^[0-9]+$", var.org_id))
    error_message = "org_id must be numeric."
  }
}

variable "billing_account" {
  type        = string
  description = "Billing account ID (012345-6789AB-CDEF01), same shape as infra/gcp/projects."
}

variable "state_bucket_name" {
  type        = string
  description = "Base name for Terraform state bucket. Project number is appended."
  default     = "cloudshortener-tf-state"
}

variable "artifacts_bucket_name" {
  type        = string
  description = "Base name for artifacts bucket. Project number is appended."
  default     = "cloudshortener-artifacts"
}

variable "region" {
  type        = string
  description = "GCS bucket location."
  default     = "europe-west1"
}

variable "allow_force_destroy" {
  type        = bool
  description = "Whether GCS buckets may be destroyed when non-empty."
  default     = false
}

variable "lifecycle_age_days_state" {
  type        = number
  description = "Delete archived state object versions older than this many days (0 = disable lifecycle rule)."
  default     = 365
}

variable "lifecycle_age_days_artifacts" {
  type        = number
  description = "Delete archived artifacts object versions older than this many days (0 = disable lifecycle rule)."
  default     = 90
}
