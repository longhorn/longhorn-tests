variable "aws_access_key" {
  type        = string
  description = "AWS ACCESS_KEY"
}

variable "aws_secret_key" {
  type        = string
  description = "AWS SECRET_KEY"
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-1a"
}

variable "aws_vpc_name" {
  type        = string
  default     = "vpc-lh-storage-network-tests"
}

variable "arch" {
  type        = string
  description = "available values (amd64, arm64)"
  default = "amd64"
}

variable "os_distro_version" {
  type        = string
  default     = "15-sp7"
}

variable "aws_ami_sles_account_number" {
  type        = string
  default     = "amazon"
}

variable "aws_instance_count" {
  type        = number
  default     = 3
}

variable "aws_instance_type" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.2xlarge for arm64"
  default     = "t2.xlarge"
}

variable "aws_ssh_public_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "aws_ssh_private_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "aws_instance_name" {
  type        = string
  default     = "lh-storage-network-tests"
}

variable "block_device_size_worker" {
  type        = number
  default     = 40
}

variable "k8s_distro_name" {
  type        = string
  default     = "k3s"
  description = "kubernetes distro version to install [k3s, rke2]  (default: k3s)"
}

variable "k8s_distro_version" {
  type        = string
  default     = "v1.34.1+k3s1"
  description = <<-EOT
    kubernetes version that will be deployed
    k3s: (default: v1.34.1+k3s1)
    rke2: (default: v1.34.1+rke2r1)
  EOT
}

variable "resources_owner" {
  type        = string
  default     = "longhorn-infra"
}

variable "cis_hardening" {
  type    = bool
  default = false
}

variable "mtu" {
  type    = string
  default = "8951"
}

variable "multus_version" {
  type    = string
  default = "v4.0.2"
}

variable "thick_plugin" {
  type    = bool
  default = true
}

variable "network_stack" {
  type      = string
  default   = "ipv4"
  validation {
    condition     = contains(["ipv4", "ipv6"], var.network_stack)
    error_message = "network_stack must be one of ipv4 or ipv6"
  }
}
