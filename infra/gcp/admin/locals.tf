locals {
  admin_services = toset([
    "storage.googleapis.com",
    "serviceusage.googleapis.com",
  ])
}
