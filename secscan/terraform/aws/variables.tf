variable "tf_workspace" {
  type        = string
}

variable "lh_aws_access_key" {
  type        = string
}

variable "lh_aws_secret_key" {
  type        = string
}

variable "aws_region" {
  type        = string
  default     = "us-east-1"
}

variable "aws_availability_zone" {
  type        = string
  default     = "us-east-1c"
}

variable "lh-secscan_aws_vpc_name" {
  type        = string
  default     = "vpc-lh-secscan"
}

variable "lh-secscan_arch" {
  type        = string
  default     = "amd64"
}

variable "distro_version" {
  type        = string
  default     = "20.04"
}

variable "aws_ami_ubuntu_account_number" {
  type        = string
  default     = "099720109477"
}

variable "lh-secscan_aws_instance_count" {
  type        = number
  default     = 1
}

variable "lh-secscan_aws_instance_name" {
  type        = string
  default     = "build_test_secscan_node"
}

variable "lh-secscan_aws_instance_type" {
  type        = string
  default     = "t3.medium"
}

variable "lh-secscan_aws_instance_root_block_device_size" {
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

variable "severity" {
  type        = string
}

variable "longhorn_version" {
  type        = string
  default     = "master"
}
