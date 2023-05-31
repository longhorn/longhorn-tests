output "cluster_name" {
  depends_on = [
    google_container_cluster.cluster,
    google_container_node_pool.node_pool
  ]
  sensitive = true
  value = google_container_cluster.cluster.name
}

output "cluster_zone" {
  depends_on = [
    google_container_cluster.cluster,
    google_container_node_pool.node_pool
  ]
  sensitive = true
  value = google_container_cluster.cluster.location
}

output "gcp_auth_file" {
  sensitive = true
  value = var.gcp_auth_file
}