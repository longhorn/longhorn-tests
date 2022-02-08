variable "build_engine_aws_access_key" {
  type        = string
  description = "AWS ACCESS_KEY"
}

variable "build_engine_aws_secret_key" {
  type        = string
  description = "AWS SECRET_KEY"
}

variable "aws_region" {
  type        = string
  default     = "us-east-2"
}

variable "tf_workspace" {
  type        = string
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-2a"
}

variable "build_engine_aws_vpc_name" {
  type        = string
  #default     = "vpc-lh-tests"
  default     = "vpc-build-test-engine"
}

variable "build_engine_arch" {
  type        = string
  description = "available values (amd64, arm64)"
}

variable "distro_version" {
  type        = string
  default     = "20.04"
}

variable "aws_ami_ubuntu_account_number" {
  type        = string
  default     = "099720109477"
}

variable "build_engine_aws_instance_count" {
  type        = number
  default     = 1
}

variable "build_engine_aws_instance_name" {
  type        = string
  default     = "build_test_engine_node"
}

variable "build_engine_aws_instance_type" {
  type        = string
  description = "Recommended instance types t2.xlarge for amd64 & a1.xlarge  for arm64"
}

variable "build_engine_aws_instance_root_block_device_size" {
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
