variable "project_id" {
  type = string
}

variable "app_name" {
  type = string
}

variable "app_env" {
  type = string
}

variable "browser_api_key_generation" {
  type        = string
  description = "Bump to force a new random suffix on the browser API key resource name (e.g. after soft-delete name collision)."
  default     = "v1"
}
