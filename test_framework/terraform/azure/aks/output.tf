output "kubeconfig" {
  depends_on = [
    azurerm_kubernetes_cluster.cluster
  ]
  value = azurerm_kubernetes_cluster.cluster.kube_config_raw
  sensitive = true
}
