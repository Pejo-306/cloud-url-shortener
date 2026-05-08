output "vpc_id" {
  value = google_compute_network.vpc.id
}

output "vpc_name" {
  value = google_compute_network.vpc.name
}

output "vpc_self_link" {
  value = google_compute_network.vpc.self_link
}

output "subnet_id" {
  value = google_compute_subnetwork.primary.id
}

output "subnet_self_link" {
  value = google_compute_subnetwork.primary.self_link
}

output "vpc_connector_id" {
  value = google_vpc_access_connector.connector.id
}

output "vpc_connector_name" {
  value = google_vpc_access_connector.connector.name
}
