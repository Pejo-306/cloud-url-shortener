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

variable "subnet_cidr" {
  type        = string
  description = "Regional subnet for workloads + private resources (spans all zones)."
  default     = "10.0.1.0/24"
}

variable "connector_cidr" {
  type        = string
  description = "Dedicated /28 for Serverless VPC Access (must not overlap VPC routes)."
  default     = "10.8.0.0/28"
}
