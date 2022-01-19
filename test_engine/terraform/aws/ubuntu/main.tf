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

# Create controlplane security group
resource "aws_security_group" "build_engine_aws_secgrp_controlplane" {
  name        = "build_engine_aws_secgrp_controlplane"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.build_engine_aws_vpc.id

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
    Name = "build_engine_aws_sec_grp_controlplane-${random_string.random_suffix.id}"
  }
}


# Create worker security group
resource "aws_security_group" "build_engine_aws_secgrp_worker" {
  name        = "build_engine_aws_secgrp_worker"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.build_engine_aws_vpc.id

  ingress {
    description = "Allow All Traffic from VPC CIDR block"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.build_engine_aws_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "build_engine_aws_sec_grp_worker-${random_string.random_suffix.id}"
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

# Create private subnet
resource "aws_subnet" "build_engine_aws_private_subnet" {
  vpc_id     = aws_vpc.build_engine_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.2.0/24"

  tags = {
    Name = "build_engine_private_subnet-${random_string.random_suffix.id}"
  }
}

# Create EIP for NATGW
resource "aws_eip" "build_engine_aws_eip_nat_gw" {
  vpc      = true

  tags = {
    Name = "build_engine_eip_nat_gw-${random_string.random_suffix.id}"
  }
}

# Create nat gateway
resource "aws_nat_gateway" "build_engine_aws_nat_gw" {
  depends_on = [
    aws_internet_gateway.build_engine_aws_igw,
    aws_eip.build_engine_aws_eip_nat_gw,
    aws_subnet.build_engine_aws_public_subnet,
    aws_subnet.build_engine_aws_private_subnet
  ]

  allocation_id = aws_eip.build_engine_aws_eip_nat_gw.id
  subnet_id     = aws_subnet.build_engine_aws_public_subnet.id

  tags = {
    Name = "build_engine_eip_nat_gw-${random_string.random_suffix.id}"
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

# Create route table for private subnets
resource "aws_route_table" "build_engine_aws_private_rt" {
  depends_on = [
    aws_nat_gateway.build_engine_aws_nat_gw
  ]

  vpc_id = aws_vpc.build_engine_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.build_engine_aws_nat_gw.id
  }

  tags = {
    Name = "build_engine_aws_private_rt-${random_string.random_suffix.id}"
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

# Assciate private subnet to private route table
resource "aws_route_table_association" "build_engine_aws_private_subnet_rt_association" {
  depends_on = [
    aws_subnet.build_engine_aws_private_subnet,
    aws_route_table.build_engine_aws_private_rt
  ]

  subnet_id      = aws_subnet.build_engine_aws_private_subnet.id
  route_table_id = aws_route_table.build_engine_aws_private_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "build_engine_aws_pair_key" {
  key_name   = format("%s_%s", "build_engine_aws_key_pair", "${random_string.random_suffix.id}")
  public_key = file(var.aws_ssh_public_key_file_path)
}

/*
# Create cluster secret (used for k3s on arm64 only)
resource "random_password" "k3s_cluster_secret" {
  length = var.arch == "arm64" ? 64 : 0
  special = false
}
*/

# Create controlplane instances
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
    aws_security_group.build_engine_aws_secgrp_controlplane.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.build_engine_aws_instance_root_block_device_size
  }

  key_name = aws_key_pair.build_engine_aws_pair_key.key_name
  user_data = file("${path.module}/user-data-scripts/provision_amd64.sh")
  #user_data = file("${var.tf_workspace}/terraform/aws/ubuntu/user-data-scripts/provision_amd64.sh")

  tags = {
    Name = "${var.build_engine_aws_instance_name}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete	= "true"
    Owner = "longhorn-infra"
  }
}

resource "aws_eip" "build_engine_aws_eip_controlplane" {
  count    = var.build_engine_aws_instance_count
  vpc      = true
}

# Associate every EIP with controlplane instance
resource "aws_eip_association" "build_engine_aws_eip_assoc" {
  depends_on = [
    aws_instance.build_engine_aws_instance,
    aws_eip.build_engine_aws_eip_controlplane
  ]

  count    = var.build_engine_aws_instance_count

  instance_id   = element(aws_instance.build_engine_aws_instance, count.index).id
  allocation_id = element(aws_eip.build_engine_aws_eip_controlplane, count.index).id
}


output "ssh_key" {
  value = var.aws_ssh_private_key_file_path
}


# wait for docker to start on instances (for rke on amd64 only)
resource "null_resource" "wait_for_docker_start" {
  depends_on = [
    aws_instance.build_engine_aws_instance,
    aws_eip.build_engine_aws_eip_controlplane,
    aws_eip_association.build_engine_aws_eip_assoc
  ]

  count = var.build_engine_aws_instance_count

  provisioner "remote-exec" {
    #inline = var.arch == "amd64" ? ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"] : null
    inline = ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"]

    connection {
      type     = "ssh"
      user     = "ubuntu"
      host     = element(aws_eip.build_engine_aws_eip_controlplane, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

