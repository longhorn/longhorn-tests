terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  access_key = var.lh_aws_access_key
  secret_key = var.lh_aws_secret_key
}

# Create a random string suffix for instance names
resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

# Create a random string for the cluster secret
resource "random_password" "cluster_secret" {
  length = 64
  special = false
}

# Create a VPC
resource "aws_vpc" "lh_aws_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "${var.lh_aws_vpc_name}-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh_aws_igw" {
  vpc_id = aws_vpc.lh_aws_vpc.id

  tags = {
    Name = "lh_igw-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create public security group
resource "aws_security_group" "lh_aws_secgrp_public" {
  name        = "lh_aws_secgrp_public"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh_aws_vpc.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow k8s API server port"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow k8s API server port"
    from_port   = 2379
    to_port     = 2379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

 ingress {
    description = "Allow k8s API server port for rke2"
    from_port   = 9345
    to_port     = 9345
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow UDP connection for longhorn-webhooks"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description = "Allow UDP connection for longhorn-webhooks"
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lh_aws_sec_grp_public-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create Public subnet
resource "aws_subnet" "lh_aws_public_subnet" {
  vpc_id     = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "lh_public_subnet-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create private subnet
resource "aws_subnet" "lh_aws_private_subnet" {
  vpc_id     = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.2.0/24"

  tags = {
    Name = "lh_private_subnet-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create route table for public subnets
resource "aws_route_table" "lh_aws_public_rt" {
  depends_on = [
    aws_internet_gateway.lh_aws_igw,
  ]

  vpc_id = aws_vpc.lh_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lh_aws_igw.id
  }

  tags = {
    Name = "lh_aws_public_rt-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Associate public subnet to public route table
resource "aws_route_table_association" "lh_aws_public_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_aws_public_subnet,
    aws_route_table.lh_aws_public_rt
  ]

  subnet_id      = aws_subnet.lh_aws_public_subnet.id
  route_table_id = aws_route_table.lh_aws_public_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "lh_aws_pair_key" {
  key_name   = format("%s_%s", "lh_aws_key_pair", "${random_string.random_suffix.id}")
  public_key = file(var.aws_ssh_public_key_file_path)

  tags = {
    Name = "lh_aws_key_pair-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

resource "aws_eip" "lh_aws_eip_controlplane" {
  count    = var.lh_aws_instance_count_controlplane
  vpc      = true

  tags = {
    Name = "lh_aws_eip_controlplane-${count.index}-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

resource "aws_ebs_volume" "lh_aws_hdd_volume" {

  count = var.use_hdd ? var.lh_aws_instance_count_worker : 0

  availability_zone = var.aws_availability_zone
  size              = 160
  type              = "st1"

  tags = {
    Name = "lh-aws-hdd-volume-${count.index}-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

# Create load balancer for rancher
resource "aws_lb_target_group" "lh_aws_lb_tg_443" {

  count = var.create_load_balancer ? 1 : 0

  name     = "lh-aws-lb-tg-443-${random_string.random_suffix.id}"
  port     = 443
  protocol = "TCP"
  vpc_id   = aws_vpc.lh_aws_vpc.id
  health_check {
    protocol = "TCP"
    port = "80"
    healthy_threshold = 3
    unhealthy_threshold = 3
    interval = 10
  }

  tags = {
    Name = "lh-aws-lb-tg-443-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

resource "aws_lb" "lh_aws_lb" {

  count = var.create_load_balancer ? 1 : 0

  depends_on = [
    aws_internet_gateway.lh_aws_igw
  ]

  name               = "lh-aws-lb-${random_string.random_suffix.id}"
  internal           = false
  load_balancer_type = "network"
  subnets            = [
    aws_subnet.lh_aws_public_subnet.id
  ]

  tags = {
    Name = "lh-aws-lb-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }
}

resource "aws_lb_listener" "lh_aws_lb_listener_443" {

  count = var.create_load_balancer ? 1 : 0

  depends_on = [
    aws_lb.lh_aws_lb,
    aws_lb_target_group.lh_aws_lb_tg_443
  ]

  load_balancer_arn = aws_lb.lh_aws_lb[0].arn
  port              = "443"
  protocol          = "TCP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.lh_aws_lb_tg_443[0].arn
  }

  tags = {
    Name = "lh-aws-lb-listener-443-${random_string.random_suffix.id}"
    Owner = "longhorn-infra"
  }

}
