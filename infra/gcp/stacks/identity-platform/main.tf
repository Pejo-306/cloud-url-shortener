# Identity Platform returns defaults for `multi_tenant` and `sign_in.phone_number`
# from it's API, even though we don't need it in our application. Without these
# explicit blocks, Terraform tries to delete them while GCP silently ignores the
# delete request, forcing perpetual drift. We set these blocks to GCP's default to
# silence the drift.
resource "google_identity_platform_config" "default" {
  project = var.project_id

  multi_tenant {
    allow_tenants = false
  }

  sign_in {
    allow_duplicate_emails = false

    email {
      enabled           = true
      password_required = true
    }

    phone_number {
      enabled            = false
      test_phone_numbers = {}
    }
  }
}

resource "random_id" "browser_api_key_suffix" {
  byte_length = 4

  keepers = {
    project_id = var.project_id
    app_name   = var.app_name
    app_env    = var.app_env
    generation = var.browser_api_key_generation
  }
}

# Browser API key for client SDK. Name includes a stable random suffix so new keys
# do not collide with soft-deleted API key names in the same project.
resource "google_apikeys_key" "browser" {
  name         = "${var.app_name}-${var.app_env}-browser-key-${random_id.browser_api_key_suffix.hex}"
  display_name = "CloudShortener client SDK API key (${var.app_env})"
  project      = var.project_id

  restrictions {
    api_targets {
      service = "identitytoolkit.googleapis.com"
    }
  }
}
