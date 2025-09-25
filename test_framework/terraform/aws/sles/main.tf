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
  assign_generated_ipv6_cidr_block = true
  enable_dns_support                = true
  enable_dns_hostnames              = true

  tags = {
    Name = "${var.lh_aws_vpc_name}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh_aws_igw" {
  vpc_id = aws_vpc.lh_aws_vpc.id

  tags = {
    Name = "lh_igw-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

# Create security group
resource "aws_security_group" "lh_aws_secgrp" {
  name        = "lh_aws_secgrp"
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
    description      = "Allow SSH over IPv6"
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow k8s API server"
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow K8s API server over IPv6"
    from_port        = 6443
    to_port          = 6443
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow k8s etcd"
    from_port   = 2379
    to_port     = 2379
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow k8s etcd over IPv6"
    from_port        = 2379
    to_port          = 2379
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow k8s API server for rke2"
    from_port   = 9345
    to_port     = 9345
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow k8s API server for rke2 over IPv6"
    from_port        = 9345
    to_port          = 9345
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow HTTP over IPv6"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow HTTPS over IPv6"
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow longhorn-ui nodeport"
    from_port   = 30000
    to_port     = 30000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description      = "Allow longhorn-ui nodeport over IPv6"
    from_port        = 30000
    to_port          = 30000
    protocol         = "tcp"
    ipv6_cidr_blocks = ["::/0"]
  }

  ingress {
    description = "Allow TCP connection for longhorn-webhooks"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description      = "Allow TCP connection for longhorn-webhooks over IPv6"
    from_port        = 0
    to_port          = 65535
    protocol         = "tcp"
    ipv6_cidr_blocks = [aws_vpc.lh_aws_vpc.ipv6_cidr_block]
  }

  ingress {
    description = "Allow UDP connection for longhorn-webhooks"
    from_port   = 0
    to_port     = 65535
    protocol    = "udp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  ingress {
    description      = "Allow UDP connection for longhorn-webhooks over IPv6"
    from_port        = 0
    to_port          = 65535
    protocol         = "udp"
    ipv6_cidr_blocks = [aws_vpc.lh_aws_vpc.ipv6_cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "lh_aws_sec_grp_controlplane-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

# Create Public subnet
resource "aws_subnet" "lh_aws_public_subnet" {
  vpc_id                          = aws_vpc.lh_aws_vpc.id
  availability_zone               = var.aws_availability_zone
  cidr_block                      = "10.0.1.0/24"
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.lh_aws_vpc.ipv6_cidr_block, 8, 0)
  assign_ipv6_address_on_creation = true

  tags = {
    Name = "lh_public_subnet-${random_string.random_suffix.id}"
    Owner = var.resources_owner
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

  route {
    ipv6_cidr_block = "::/0"
    gateway_id      = aws_internet_gateway.lh_aws_igw.id
  }

  tags = {
    Name = "lh_aws_public_rt-${random_string.random_suffix.id}"
    Owner = var.resources_owner
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
    Owner = var.resources_owner
  }
}

resource "aws_eip" "lh_aws_eip_controlplane" {
  count    = var.lh_aws_instance_count_controlplane
  vpc      = true

  tags = {
    Name = "lh_aws_eip_controlplane-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_ebs_volume" "lh_aws_hdd_volume" {

  count = var.use_hdd ? var.lh_aws_instance_count_worker : 0

  availability_zone = var.aws_availability_zone
  size              = 160
  type              = "st1"

  tags = {
    Name = "lh-aws-hdd-volume-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_ebs_volume" "lh_aws_ssd_volume" {

  count = var.extra_block_device ? var.lh_aws_instance_count_worker : 0

  availability_zone = var.aws_availability_zone
  size              = var.block_device_size_worker
  type              = "gp3"

  tags = {
    Name = "lh-aws-ssd-volume-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
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
    Owner = var.resources_owner
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
    Owner = var.resources_owner
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
    Owner = var.resources_owner
  }

}
