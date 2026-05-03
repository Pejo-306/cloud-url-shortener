resource "google_storage_bucket" "frontend" {
  project                     = var.project_id
  name                        = local.bucket_name
  location                    = var.region
  uniform_bucket_level_access = true
  labels                      = var.labels

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  versioning {
    enabled = true
  }

  force_destroy = local.allow_force_destroy
}

resource "google_storage_bucket_iam_member" "lb_object_viewer" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = local.lb_data_plane_sa
}

resource "google_compute_backend_bucket" "cdn_lb_backend" {
  project     = var.project_id
  name        = "${local.fe_prefix}-cdn"
  bucket_name = google_storage_bucket.frontend.name
  enable_cdn  = true

  cdn_policy {
    cache_mode        = "CACHE_ALL_STATIC"
    default_ttl       = 3600
    max_ttl           = 86400
    client_ttl        = 3600
    negative_caching  = true
    serve_while_stale = 86400
  }
}

resource "google_compute_url_map" "route_table" {
  project         = var.project_id
  name            = "${local.fe_prefix}-route-table"
  default_service = google_compute_backend_bucket.cdn_lb_backend.id

  # Redirect missing paths to index.html and let Vue Router handle it.
  default_custom_error_response_policy {
    error_response_rule {
      match_response_codes   = ["403"]
      path                   = "/index.html"
      override_response_code = 200
    }
    error_response_rule {
      match_response_codes   = ["404"]
      path                   = "/index.html"
      override_response_code = 200
    }
    error_service = google_compute_backend_bucket.cdn_lb_backend.id
  }
}

resource "google_compute_global_address" "lb_ip" {
  project = var.project_id
  name    = "${local.fe_prefix}-ip"
}

resource "google_compute_managed_ssl_certificate" "lb_ssl_cert" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-cert"

  managed {
    domains = [var.frontend_domain]
  }
}

resource "google_compute_target_https_proxy" "https" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-https-proxy"

  url_map          = google_compute_url_map.route_table.id
  ssl_certificates = [google_compute_managed_ssl_certificate.lb_ssl_cert[0].id]
}

resource "google_compute_target_http_proxy" "http_redirect" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-http-proxy"

  url_map = google_compute_url_map.http_redirect[0].id
}

resource "google_compute_url_map" "http_redirect" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-http-redirect-table"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_global_forwarding_rule" "https" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-https-rule"

  ip_address            = google_compute_global_address.lb_ip.address
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.https[0].id
}

resource "google_compute_global_forwarding_rule" "http" {
  count   = local.use_custom_domain ? 1 : 0
  project = var.project_id
  name    = "${local.fe_prefix}-http-rule"

  ip_address            = google_compute_global_address.lb_ip.address
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.http_redirect[0].id
}

# No custom domain: serve HTTP on the global IP (dev / lab only).
resource "google_compute_target_http_proxy" "http_only" {
  count   = local.use_custom_domain ? 0 : 1
  project = var.project_id
  name    = "${local.fe_prefix}-http-only-proxy"

  url_map = google_compute_url_map.route_table.id
}

resource "google_compute_global_forwarding_rule" "http_only" {
  count   = local.use_custom_domain ? 0 : 1
  project = var.project_id
  name    = "${local.fe_prefix}-http-only-rule"

  ip_address            = google_compute_global_address.lb_ip.address
  ip_protocol           = "TCP"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.http_only[0].id
}
