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
  access_key = var.build_engine_aws_access_key
  secret_key = var.build_engine_aws_secret_key
}

# Create a random string suffix for instance names
resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

# Create a VPC
resource "aws_vpc" "build_engine_aws_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "${var.build_engine_aws_vpc_name}-${random_string.random_suffix.id}"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "build_engine_aws_igw" {
  vpc_id = aws_vpc.build_engine_aws_vpc.id

  tags = {
    Name = "build_engine_igw"
  }
}

# Create build_node security group
resource "aws_security_group" "build_engine_aws_secgrp" {
  name        = "build_engine_aws_secgrp"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.build_engine_aws_vpc.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "build_engine_aws_sec_grp_build_node-${random_string.random_suffix.id}"
  }
}

# Create Public subnet
resource "aws_subnet" "build_engine_aws_public_subnet" {
  vpc_id     = aws_vpc.build_engine_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "build_engine_public_subnet-${random_string.random_suffix.id}"
  }
}

# Create route table for public subnets
resource "aws_route_table" "build_engine_aws_public_rt" {
  depends_on = [
    aws_internet_gateway.build_engine_aws_igw,
  ]

  vpc_id = aws_vpc.build_engine_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.build_engine_aws_igw.id
  }

  tags = {
    Name = "build_engine_aws_public_rt-${random_string.random_suffix.id}"
  }
}

# Assciate public subnet to public route table
resource "aws_route_table_association" "build_engine_aws_public_subnet_rt_association" {
  depends_on = [
    aws_subnet.build_engine_aws_public_subnet,
    aws_route_table.build_engine_aws_public_rt
  ]

  subnet_id      = aws_subnet.build_engine_aws_public_subnet.id
  route_table_id = aws_route_table.build_engine_aws_public_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "build_engine_aws_pair_key" {
  key_name   = format("%s_%s", "build_engine_aws_key_pair", "${random_string.random_suffix.id}")
  public_key = file(var.aws_ssh_public_key_file_path)
}

# Create build_node instances
resource "aws_instance" "build_engine_aws_instance" {
 depends_on = [
    aws_subnet.build_engine_aws_public_subnet,
  ]

  count = var.build_engine_aws_instance_count

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.build_engine_aws_instance_type

  subnet_id = aws_subnet.build_engine_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.build_engine_aws_secgrp.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.build_engine_aws_instance_root_block_device_size
  }

  key_name = aws_key_pair.build_engine_aws_pair_key.key_name
  user_data = file("${path.module}/user-data-scripts/provision.sh")
  
  tags = {
    Name = "${var.build_engine_aws_instance_name}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete	= "true"
    Owner = "longhorn-infra"
  }
}

resource "aws_eip" "build_engine_aws_eip_build_node" {
  count    = var.build_engine_aws_instance_count
  vpc      = true
}

# Associate every EIP with build_node instance
resource "aws_eip_association" "build_engine_aws_eip_assoc" {
  depends_on = [
    aws_instance.build_engine_aws_instance,
    aws_eip.build_engine_aws_eip_build_node
  ]

  count    = var.build_engine_aws_instance_count

  instance_id   = element(aws_instance.build_engine_aws_instance, count.index).id
  allocation_id = element(aws_eip.build_engine_aws_eip_build_node, count.index).id
}

# wait for docker to start on instances (for rke on amd64 only)
resource "null_resource" "wait_for_docker_start" {
  depends_on = [
    aws_instance.build_engine_aws_instance,
    aws_eip.build_engine_aws_eip_build_node,
    aws_eip_association.build_engine_aws_eip_assoc
  ]

  count = var.build_engine_aws_instance_count

  provisioner "remote-exec" {
    inline = ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = element(aws_eip.build_engine_aws_eip_build_node, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

# build engine base image with different commit ID
resource "null_resource" "build_images" {
  depends_on = [
    null_resource.wait_for_docker_start,
    aws_eip.build_engine_aws_eip_build_node,
  ]

  count = var.build_engine_aws_instance_count

  provisioner "file" {
    source      = "${var.tf_workspace}/scripts/generate_images.sh"
    destination = "/tmp/generate_images.sh"

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = element(aws_eip.build_engine_aws_eip_build_node, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "remote-exec" {
    inline = [
        "sudo chmod +x /tmp/generate_images.sh",
        "sudo /tmp/generate_images.sh ${var.build_engine_arch} ${var.docker_id} ${var.docker_password} ${var.docker_repo} ${var.commit_id}"
    ]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = element(aws_eip.build_engine_aws_eip_build_node, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}