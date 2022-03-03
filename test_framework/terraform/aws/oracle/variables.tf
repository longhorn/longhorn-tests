variable "lh_aws_access_key" {
  type        = string
  description = "AWS ACCESS_KEY"
}

variable "lh_aws_secret_key" {
  type        = string
  description = "AWS SECRET_KEY"
}

variable "aws_region" {
  type        = string
  default     = "us-east-2"
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-2a"
}

variable "lh_aws_vpc_name" {
  type        = string
  default     = "vpc-lh-tests"
}

variable "arch" {
  type        = string
  description = "available values (amd64, arm64)"
}

variable "distro_version" {
  type        = string
  default     = "8.3"
}

variable "aws_ami_oraclelinux_account_number" {
  type        = string
  default     = "131827586825"
}

variable "lh_aws_instance_count_controlplane" {
  type        = number
  default     = 1
}

variable "lh_aws_instance_count_worker" {
  type        = number
  default     = 3
}

variable "lh_aws_instance_name_controlplane" {
  type        = string
  default     = "lh-tests-controlplane"
}

variable "lh_aws_instance_type_controlplane" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
}

variable "lh_aws_instance_type_worker" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
}

variable "lh_aws_instance_root_block_device_size_controlplane" {
  type        = number
  default     = 40
}

variable "aws_ssh_public_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "aws_ssh_private_key_file_path" {
  type        = string
  default     = "~/.ssh/id_rsa"
}

variable "lh_aws_instance_name_worker" {
  type        = string
  default     = "lh-tests-worker"
}

variable "lh_aws_instance_root_block_device_size_worker" {
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
  default     = "v1.23.1+k3s2"
  description = <<-EOT
    kubernetes version that will be deployed
    rke: (default: v1.22.5-rancher1-1)
    k3s: (default: v1.23.1+k3s2)
    rke2: (default: v1.23.3+rke2r1)
  EOT
}
