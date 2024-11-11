variable "lab_url" {
  type        = string
  description = "LAB URL"
  sensitive   = true
}

variable "lab_access_key" {
  type        = string
  description = "LAB ACCESS_KEY"
  sensitive   = true
}

variable "lab_secret_key" {
  type        = string
  description = "LAB SECRET_KEY"
  sensitive   = true
}

variable "ssh_public_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "arch" {
  type        = string
  description = "available values (amd64, arm64)"
  default     = "amd64"
}

variable "os_distro_version" {
  type        = string
  default     = "9.4"
}

variable "k8s_distro_name" {
  type        = string
  default     = "rke2"
  description = "kubernetes distro version to install [rke2, k3s]  (default: rke2)"
}

variable "k8s_distro_version" {
  type        = string
  default     = "v1.28.14+rke2r1"
  description = <<-EOT
    kubernetes version that will be deployed
    k3s: (default: v1.28.14+k3s1)
    rke2: (default: v1.28.14+rke2r1)
  EOT
}
