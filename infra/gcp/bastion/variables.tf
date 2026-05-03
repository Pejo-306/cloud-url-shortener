variable "project_id" {
  type = string
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

variable "app_env" {
  type = string
}

variable "region" {
  type = string
}

variable "zone" {
  type        = string
  description = "Zone for the bastion VM (e.g. europe-west1-b)."
  default     = ""
}

variable "subnet_self_link" {
  type        = string
  description = "Private subnet self link (from network stack output)."
}

variable "machine_type" {
  type    = string
  default = "e2-micro"
}

variable "image" {
  type        = string
  description = "Boot disk image for the bastion VM. Use an image self link or family path."
  default     = "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64"
}

variable "labels" {
  type        = map(string)
  description = "Labels for the bastion VM (optional)."
  default     = {}
}
