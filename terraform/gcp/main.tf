terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  cluster_name = var.cluster_name != "" ? var.cluster_name : "signalharbor-${var.environment}"

  labels = {
    project     = "signal-harbor"
    environment = var.environment
    managed-by  = "terraform"
  }
}

# ---------------------------------------------------------------------------
# VPC Network
# ---------------------------------------------------------------------------
resource "google_compute_network" "signalharbor" {
  name                    = "signalharbor-${var.environment}"
  auto_create_subnetworks = false
  project                 = var.project_id
}

resource "google_compute_subnetwork" "signalharbor" {
  name          = "signalharbor-${var.environment}-subnet"
  ip_cidr_range = "10.2.0.0/16"
  region        = var.region
  network       = google_compute_network.signalharbor.id
  project       = var.project_id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.3.0.0/16"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.4.0.0/20"
  }
}

# ---------------------------------------------------------------------------
# Service Account for GKE nodes
# ---------------------------------------------------------------------------
resource "google_service_account" "signalharbor" {
  account_id   = "signalharbor-${var.environment}"
  display_name = "Signal Harbor GKE SA"
  project      = var.project_id
}

resource "google_project_iam_member" "signalharbor_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.signalharbor.email}"
}

resource "google_project_iam_member" "signalharbor_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.signalharbor.email}"
}

# ---------------------------------------------------------------------------
# GKE Autopilot Cluster
# ---------------------------------------------------------------------------
resource "google_container_cluster" "signalharbor" {
  name     = local.cluster_name
  location = var.region
  project  = var.project_id

  enable_autopilot = true

  network    = google_compute_network.signalharbor.id
  subnetwork = google_compute_subnetwork.signalharbor.id

  deletion_protection = var.environment == "prod"

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  release_channel {
    channel = var.environment == "prod" ? "STABLE" : "REGULAR"
  }
}

# ---------------------------------------------------------------------------
# Cloud SQL PostgreSQL 16
# ---------------------------------------------------------------------------
resource "google_sql_database_instance" "signalharbor" {
  name             = "signalharbor-${var.environment}"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  deletion_protection = var.environment == "prod"

  settings {
    tier      = var.db_tier
    disk_size = var.db_disk_gb

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "prod"
      transaction_log_retention_days = var.environment == "prod" ? 7 : 1
    }

    ip_configuration {
      ssl_mode        = "ENCRYPTED_ONLY"
      ipv4_enabled    = false
      private_network = google_compute_network.signalharbor.id
    }

    availability_type = var.environment == "prod" ? "REGIONAL" : "ZONAL"

    database_flags {
      name  = "max_connections"
      value = "100"
    }

    user_labels = local.labels
  }
}

resource "google_sql_database" "signalharbor" {
  name     = "signalharbor"
  instance = google_sql_database_instance.signalharbor.name
  project  = var.project_id
}

resource "google_sql_user" "signalharbor" {
  name     = var.db_username
  instance = google_sql_database_instance.signalharbor.name
  password = var.db_password
  project  = var.project_id
}

# ---------------------------------------------------------------------------
# Memorystore Redis 7
# ---------------------------------------------------------------------------
resource "google_redis_instance" "signalharbor" {
  name           = "signalharbor-${var.environment}"
  tier           = var.environment == "prod" ? "STANDARD_HA" : "BASIC"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  project        = var.project_id

  redis_version = "REDIS_7_0"

  authorized_network = google_compute_network.signalharbor.id

  transit_encryption_mode = "SERVER_AUTHENTICATION"

  labels = local.labels
}

# ---------------------------------------------------------------------------
# Kubernetes provider — auth via GKE data source
# ---------------------------------------------------------------------------
data "google_client_config" "default" {}

provider "kubernetes" {
  host  = "https://${google_container_cluster.signalharbor.endpoint}"
  token = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(
    google_container_cluster.signalharbor.master_auth[0].cluster_ca_certificate
  )
}

# ---------------------------------------------------------------------------
# Application module
# ---------------------------------------------------------------------------
module "app" {
  source = "../modules/k8s-app"

  namespace    = "signalharbor-${var.environment}"
  image        = "ghcr.io/gerardrecinto/signal-harbor:${var.app_version}"
  replicas     = var.environment == "prod" ? 3 : 2
  app_port     = 80
  ingress_host = var.ingress_host

  api_key      = var.api_key
  database_url = "postgresql://${var.db_username}:${var.db_password}@${google_sql_database_instance.signalharbor.private_ip_address}:5432/signalharbor"
  redis_url    = "rediss://${google_redis_instance.signalharbor.host}:${google_redis_instance.signalharbor.port}"

  depends_on = [google_container_cluster.signalharbor]
}
