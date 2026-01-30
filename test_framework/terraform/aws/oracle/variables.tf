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
  default     = "us-east-1"
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-1a"
}

variable "lh_aws_vpc_name" {
  type        = string
  default     = "vpc-lh-tests"
}

variable "arch" {
  type        = string
  description = "available values (amd64, arm64)"
  default     = "amd64"
}

variable "os_distro_version" {
  type        = string
  default     = "10.0"
}

variable "aws_ami_oraclelinux_account_number" {
  type        = string
  default     = "679593333241"
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
  description = "Recommended instance types t2.xlarge for amd64 & a1.2xlarge for arm64"
  default     = "t2.xlarge"
}

variable "lh_aws_instance_type_worker" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.2xlarge for arm64"
  default     = "t2.xlarge"
}

variable "block_device_size_controlplane" {
  type        = number
  default     = 64
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

variable "block_device_size_worker" {
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
  default     = "v1.34.2+k3s1"
  description = <<-EOT
    kubernetes version that will be deployed
    k3s: (default: v1.34.2+k3s1)
    rke2: (default: v1.34.2+rke2r1)
  EOT
}

variable "use_hdd" {
  type    = bool
  default = false
}

variable "create_load_balancer" {
  type    = bool
  default = false
}

variable "custom_ssh_public_key" {
  type = string
  default = ""
  sensitive = true
}

variable "extra_block_device" {
  type = bool
  default = true
}
