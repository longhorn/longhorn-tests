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
  default     = "1.7.6"
}

variable "aws_ami_talos_account_number" {
  type        = string
  default     = "641769369267"
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

variable "lh_aws_instance_name_worker" {
  type        = string
  default     = "lh-tests-worker"
}

variable "lh_aws_instance_type_controlplane" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
  default     = "t2.xlarge"
}

variable "lh_aws_instance_type_worker" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
  default     = "t2.xlarge"
}

variable "lh_aws_instance_root_block_device_size_controlplane" {
  type        = number
  default     = 40
}

variable "lh_aws_instance_root_block_device_size_worker" {
  type        = number
  default     = 40
}

variable "k8s_distro_version" {
  type        = string
  default     = "v1.30.0"
}

variable "use_hdd" {
  type    = bool
  default = false
}

variable "create_load_balancer" {
  type    = bool
  default = false
}

variable "resources_owner" {
  type        = string
  default     = "longhorn-infra"
}
