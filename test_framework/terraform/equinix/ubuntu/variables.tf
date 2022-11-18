variable "k8s_distro_name" {
  type        = string
  default     = "rke2"
  description = "kubernetes distro version to install [rke2, k3s]  (default: rke2)"
}

variable "k8s_distro_version" {
  type        = string
  default     = "v1.24.7+rke2r1"
  description = <<-EOT
    kubernetes version that will be deployed
    rke2: (default: v1.24.7+rke2r1)
    k3s: (default: v1.24.7+k3s1)
  EOT
}

variable "os_distro_version" {
  type = string
  default = "22.04"
}

variable "metro" {
  type = string
  default = "da"
}

variable "equinix_project_id" {
  type = string
}

variable "equinix_auth_token" {
  type = string
}

variable "instance_name_controlplane" {
  type        = string
  default     = "lh-tests-controlplane"
}

variable "instance_name_worker" {
  type        = string
  default     = "lh-tests-worker"
}

variable "instance_type_controlplane" {
  type = string
  default = "c3.small.x86"
  description = <<-EOT
    select a machine type to run the control plane
    since benchmark test is not run on control plane, the architecture or the machine type doesn't matter
    c3.small.x86 can be used to save costs
  EOT
}

variable "instance_type_worker" {
  type = string
  default = "m3.large.x86"
  description = <<-EOT
    select a machine type with nvme storage to run the test
    for amd64, use m3.large.x86
    for arm64, use c3.large.arm64
  EOT
}

variable "worker_count" {
  type        = number
  default     = 3
}

variable "ssh_public_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "ssh_private_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa"
}