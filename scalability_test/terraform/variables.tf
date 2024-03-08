variable "lh_aws_access_key" {
  type        = string
  description = "AWS ACCESS_KEY"
}

variable "lh_aws_secret_key" {
  type        = string
  description = "AWS SECRET_KEY"
}

variable "aws_region" {
  type    = string
  default = "us-west-2"
}

variable "aws_availability_zone" {
  type    = string
  default = "us-west-2a"
}

variable "distro_version" {
  type    = string
  default = "20.04"
}

variable "aws_ami_ubuntu_account_number" {
  type    = string
  default = "099720109477"
}

variable "lh_aws_instance_count_controlplane" {
  type    = number
  default = 1
}

variable "lh_aws_instance_count_worker" {
  type    = number
  default = 3
}

variable "lh_aws_instance_name_controlplane" {
  type    = string
  default = "lh-tests-controlplane"
}

variable "lh_aws_instance_type_controlplane" {
  type    = string
  default = "t2.xlarge"
}

variable "lh_aws_instance_type_worker" {
  type    = string
  default = "t2.xlarge"
}

variable "lh_aws_instance_root_block_device_size_controlplane" {
  type    = number
  default = 20
}

variable "aws_ssh_public_key_file_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}

variable "aws_ssh_private_key_file_path" {
  type    = string
  default = "~/.ssh/id_rsa"
}

variable "lh_aws_instance_name_worker" {
  type    = string
  default = "lh-tests-worker"
}

variable "lh_aws_instance_root_block_device_size_worker" {
  type    = number
  default = 40
}

variable "lh_aws_create_ebs_block_device" {
  type    = bool
  default = false
}

variable "lh_aws_ebs_block_device_settings" {
  type = map(any)
  default = {
    device_name           = "/dev/sdh"
    os_device_name = "/dev/nvme1n1" // The name of the block device as appeared inside the OS
    volume_size           = 50
    delete_on_termination = true
    volume_type = "gp3"
    iops = 3000
    throughput = 125
  }
}

variable "rke2_version" {
  type    = string
  default = "v1.21.5+rke2r1"
}
