output "instance_name" {
  value = google_compute_instance.bastion.name
}

output "instance_id" {
  value = google_compute_instance.bastion.instance_id
}

output "zone" {
  value = google_compute_instance.bastion.zone
}

output "service_account_email" {
  value = google_service_account.bastion.email
}
