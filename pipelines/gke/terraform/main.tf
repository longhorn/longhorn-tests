provider "google" {
  project     = var.gcp_project
  credentials = file(var.gcp_auth_file)
  region      = var.gcp_region
}

provider "google-beta" {
  project     = var.gcp_project
  credentials = file(var.gcp_auth_file)
  region      = var.gcp_region
}

data "google_client_config" "provider" {}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

data "google_compute_zones" "available" {
}

resource "google_compute_network" "vpc_network" {
  name = "${var.test_name}-${random_string.random_suffix.id}-network"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnetwork" {
  name          = "${var.test_name}-${random_string.random_suffix.id}-subnetwork"
  ip_cidr_range = "10.2.0.0/16"
  region        = var.gcp_region
  network       = google_compute_network.vpc_network.id
}

resource "google_container_cluster" "cluster" {

  provider = google-beta

  name               = "${var.test_name}-${random_string.random_suffix.id}-cluster"
  network            = google_compute_network.vpc_network.id
  subnetwork         = google_compute_subnetwork.subnetwork.id
  location           = data.google_compute_zones.available.names[0]
  remove_default_node_pool = true
  initial_node_count       = 1
  cluster_autoscaling {
    autoscaling_profile = "OPTIMIZE_UTILIZATION"
  }
}

resource "google_container_node_pool" "node_pool" {
  name       = "${var.test_name}-${random_string.random_suffix.id}-node-pool"
  cluster    = google_container_cluster.cluster.id
  node_count = 3

  autoscaling {
    min_node_count = 3
    max_node_count = 8
  }

  node_config {
    machine_type = "e2-standard-2"
    image_type = "UBUNTU_CONTAINERD"
  }
}
