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
  default     = "15-sp5"
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
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
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

variable "aws_instance_root_block_device_size" {
  type        = number
  default     = 40
}

variable "k8s_distro_name" {
  type        = string
  default     = "k3s"
  description = "kubernetes distro version to install [rke, k3s, rke2]  (default: k3s)"
}

variable "k8s_distro_version" {
  type        = string
  default     = "v1.27.1+k3s1"
  description = <<-EOT
    kubernetes version that will be deployed
    rke: (default: v1.22.5-rancher1-1)
    k3s: (default: v1.27.1+k3s1)
    rke2: (default: v1.27.2+rke2r1)
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