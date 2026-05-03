resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = "${var.app_name}-${var.app_env}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "primary" {
  project       = var.project_id
  name          = "${var.app_name}-${var.app_env}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id
}

resource "google_compute_router" "router" {
  project = var.project_id
  name    = "${var.app_name}-${var.app_env}-router"
  region  = var.region
  network = google_compute_network.vpc.id
}

resource "google_compute_router_nat" "nat" {
  project = var.project_id
  name    = "${var.app_name}-${var.app_env}-nat"
  router  = google_compute_router.router.name
  region  = var.region

  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Allow SSH via IAP tunnel for optional bastion (TCP 22)
resource "google_compute_firewall" "allow_iap_ssh" {
  project = var.project_id
  name    = "${var.app_name}-${var.app_env}-firewall-allow-iap-ssh"
  network = google_compute_network.vpc.name

  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["35.235.240.0/20"] # IAP CIDR range for all of GCP
  target_tags   = ["bastion"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# Allow ingress traffic in the primary subnet.
resource "google_compute_firewall" "allow_internal_ingress" {
  project = var.project_id
  name    = "${var.app_name}-${var.app_env}-firewall-allow-internal-ingress"
  network = google_compute_network.vpc.name

  direction     = "INGRESS"
  priority      = 1000
  source_ranges = [var.subnet_cidr]

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }
}

resource "google_vpc_access_connector" "connector" {
  project = var.project_id
  name    = local.vpc_access_connector_name
  region  = var.region

  network       = google_compute_network.vpc.name
  ip_cidr_range = var.connector_cidr

  min_throughput = 200
  max_throughput = 300
}
