provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "bastion" {
  project      = var.project_id
  account_id   = local.bastion_account_id
  display_name = "Bastion host (${var.app_env})"
}

resource "google_project_iam_member" "bastion_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.bastion.email}"
}

resource "google_compute_instance" "bastion" {
  project      = var.project_id
  name         = "${var.app_name}-${var.app_env}-bastion"
  machine_type = var.machine_type
  zone         = local.zone

  labels = var.labels
  tags   = ["bastion"]

  boot_disk {
    initialize_params {
      image = var.image
    }
  }

  network_interface {
    subnetwork = var.subnet_self_link
  }

  service_account {
    email  = google_service_account.bastion.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  scheduling {
    preemptible = false
  }

  # Optional tooling for Memorystore / Redis debugging via IAP SSH (packages are best-effort).
  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq redis-tools curl || true
  EOT

  allow_stopping_for_update = true
}
