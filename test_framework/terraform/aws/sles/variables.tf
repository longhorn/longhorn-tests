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
  default     = "vpc-longhorn-tests"
}

variable "arch" {
  type        = string
  description = "available values (amd64, arm64)"
}

variable "distro_version" {
  type        = string
  default     = "15-sp3-v20210622"
}

variable "aws_ami_sles_account_number" {
  type        = string
  default     = "amazon"
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
  default     = "longhorn-tests-controlplane"
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
  default     = "longhorn-tests-worker"
}

variable "lh_aws_instance_root_block_device_size_worker" {
  type        = number
  default     = 40
}

variable "rke_k8s_version" {
  type        = string
  default     = "v1.20.8-rancher1-1"
  description = "RKE k8s version will be used to generate RKE config file output"
}

variable "k3s_version" {
  type        = string
  default     = "v1.20.8+k3s1"
}
