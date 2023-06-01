variable "azure_client_id" {
  type    = string
  sensitive = true
}

variable "azure_crt_path" {
  type    = string
  sensitive = true
}

variable "azure_crt_password" {
  type    = string
  sensitive = true
}

variable "azure_tenant_id" {
  type    = string
  sensitive = true
}

variable "azure_subscription_id" {
  type    = string
  sensitive = true
}

variable "test_name" {
  type        = string
  default     = "lh-aks-tests"
}
