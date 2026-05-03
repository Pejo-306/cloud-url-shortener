locals {
  zone               = var.zone != "" ? var.zone : "${var.region}-b"
  bastion_account_id = "bastion-${var.app_env}"
}
