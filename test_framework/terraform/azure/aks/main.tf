terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.0.0"
    }
  }
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {}

  client_id                   = var.azure_client_id
  client_certificate_path     = var.azure_crt_path
  client_certificate_password = var.azure_crt_password
  tenant_id                   = var.azure_tenant_id
  subscription_id             = var.azure_subscription_id
}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

resource "azurerm_resource_group" "resource_group" {
  name     = "${var.test_name}-${random_string.random_suffix.id}-resources"
  location = "Southeast Asia"
}

resource "azurerm_kubernetes_cluster" "cluster" {
  name                = "${var.test_name}-${random_string.random_suffix.id}-cluster"
  location            = azurerm_resource_group.resource_group.location
  resource_group_name = azurerm_resource_group.resource_group.name
  dns_prefix          = "${var.test_name}-${random_string.random_suffix.id}"

  default_node_pool {
    name       = "default"
    node_count = 3
    vm_size    = "Standard_D3_v2"
    enable_auto_scaling = true
    max_count = 8
    min_count = 3
    type = "VirtualMachineScaleSets"
  }

  identity {
    type = "SystemAssigned"
  }

  auto_scaler_profile {
    skip_nodes_with_system_pods = false
    skip_nodes_with_local_storage = false
    scan_interval = "10s"
    scale_down_delay_after_add = "1m"
    scale_down_unneeded = "1m"
  }
}
