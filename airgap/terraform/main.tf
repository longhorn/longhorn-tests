terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
    digitalocean = {
      source = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

data "aws_availability_zones" "available" {
  state = "available"
}

provider "digitalocean" {
  token = var.do_token
}

locals {
  registry_username = "registry_user"
  registry_password = random_string.registry_password.id
}

resource "random_string" "registry_password" {
  length           = 16
  special          = false
  lower            = true
  upper            = false
}

# Create a random string suffix for instance names
resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

# Create a VPC
resource "aws_vpc" "lh_registry_aws_vpc" {

  cidr_block = "10.0.0.0/16"
  enable_dns_hostnames = true

  tags = {
    Name = "lh-registry-vpc-${random_string.random_suffix.id}"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh_registry_aws_igw" {
  vpc_id = aws_vpc.lh_registry_aws_vpc.id

  tags = {
    Name = "lh-registry-igw-${random_string.random_suffix.id}"
  }
}

# Create registry security group
resource "aws_security_group" "lh_registry_aws_secgrp" {
  name        = "lh_registry_aws_secgrp_${random_string.random_suffix.id}"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh_registry_aws_vpc.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow TCP connection for longhorn-webhooks"
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
    Name = "lh-registry-secgrp-${random_string.random_suffix.id}"
  }
}

# Create Public subnet
resource "aws_subnet" "lh_registry_aws_public_subnet" {
  vpc_id     = aws_vpc.lh_registry_aws_vpc.id
  availability_zone = data.aws_availability_zones.available.names[0]
  cidr_block = "10.0.1.0/24"

  map_public_ip_on_launch = true

  tags = {
    Name = "lh-registry-public-subnet-${random_string.random_suffix.id}"
  }
}

# Create private subnet
resource "aws_subnet" "lh_registry_aws_private_subnet" {
  vpc_id     = aws_vpc.lh_registry_aws_vpc.id
  availability_zone = data.aws_availability_zones.available.names[1]
  cidr_block = "10.0.2.0/24"

  map_public_ip_on_launch = true

  tags = {
    Name = "lh-registry-private-subnet-${random_string.random_suffix.id}"
  }
}

# Create route table for public subnets
resource "aws_route_table" "lh_registry_aws_public_rt" {
  depends_on = [
    aws_internet_gateway.lh_registry_aws_igw,
  ]

  vpc_id = aws_vpc.lh_registry_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lh_registry_aws_igw.id
  }

  tags = {
    Name = "lh-registry-aws-public-rt-${random_string.random_suffix.id}"
  }
}

# Create route table for private subnets
resource "aws_route_table" "lh_registry_aws_private_rt" {
  depends_on = [
    aws_internet_gateway.lh_registry_aws_igw
  ]

  vpc_id = aws_vpc.lh_registry_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lh_registry_aws_igw.id
  }

  tags = {
    Name = "lh-registry-aws-private-rt-${random_string.random_suffix.id}"
  }
}

# Associate public subnet to public route table
resource "aws_route_table_association" "lh_registry_aws_public_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_registry_aws_public_subnet,
    aws_route_table.lh_registry_aws_public_rt
  ]

  subnet_id      = aws_subnet.lh_registry_aws_public_subnet.id
  route_table_id = aws_route_table.lh_registry_aws_public_rt.id
}

# Associate private subnet to private route table
resource "aws_route_table_association" "lh_registry_aws_private_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_registry_aws_private_subnet,
    aws_route_table.lh_registry_aws_private_rt
  ]

  subnet_id      = aws_subnet.lh_registry_aws_private_subnet.id
  route_table_id = aws_route_table.lh_registry_aws_private_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "lh_registry_aws_pair_key" {
  key_name   = format("%s_%s", "lh_registry_aws_key_pair", random_string.random_suffix.id)
  public_key = file(var.aws_ssh_public_key_file_path)
}

# Create instance for registry
resource "aws_instance" "lh_registry_aws_instance" {

  depends_on = [
    aws_subnet.lh_registry_aws_public_subnet,
  ]

  availability_zone = data.aws_availability_zones.available.names[0]

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.registry_aws_instance_type
  associate_public_ip_address = true

  subnet_id = aws_subnet.lh_registry_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_registry_aws_secgrp.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = 40
  }

  key_name = aws_key_pair.lh_registry_aws_pair_key.key_name

  tags = {
    Name = "lh-registry-${random_string.random_suffix.id}"
  }
}

data "digitalocean_domain" "rancher_domain" {
  name = "ci-qa.rancher.space"
}

resource "digitalocean_record" "lh_registry" {

  depends_on = [
    aws_instance.lh_registry_aws_instance
  ]

  domain = data.digitalocean_domain.rancher_domain.id
  type   = "A"
  name   = "lh-registry-${random_string.random_suffix.id}"
  value  = aws_instance.lh_registry_aws_instance.public_ip
  ttl    = 60
}

# post setup
resource "null_resource" "post_setup" {

  depends_on = [
    aws_instance.lh_registry_aws_instance,
    digitalocean_record.lh_registry
  ]

  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then cat /var/log/cloud-init-output.log; fi",
      "echo \"cloud-init completed!\";"
    ]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_instance.lh_registry_aws_instance.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "file" {
    source      = "${path.module}/user-data-scripts/provision_registry_server.sh"
    destination = "/tmp/provision_registry_server.sh"

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_instance.lh_registry_aws_instance.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/provision_registry_server.sh",
      "registry_username=${local.registry_username} registry_password=${local.registry_password} registry_url=${digitalocean_record.lh_registry.fqdn} longhorn_version=${var.longhorn_version} /tmp/provision_registry_server.sh",
    ]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = aws_instance.lh_registry_aws_instance.public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

}
