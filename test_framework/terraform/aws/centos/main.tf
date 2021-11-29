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

# Create a VPC
resource "aws_vpc" "lh_aws_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "${var.lh_aws_vpc_name}-${random_string.random_suffix.id}"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh_aws_igw" {
  vpc_id = aws_vpc.lh_aws_vpc.id

  tags = {
    Name = "lh_igw"
  }
}

# Create controlplane security group
resource "aws_security_group" "lh_aws_secgrp_controlplane" {
  name        = "lh_aws_secgrp_controlplane"
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


  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lh_aws_sec_grp_controlplane-${random_string.random_suffix.id}"
  }
}


# Create worker security group
resource "aws_security_group" "lh_aws_secgrp_worker" {
  name        = "lh_aws_secgrp_worker"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh_aws_vpc.id

  ingress {
    description = "Allow All Traffic from VPC CIDR block"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [aws_vpc.lh_aws_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lh_aws_sec_grp_worker-${random_string.random_suffix.id}"
  }
}


# Create Public subnet
resource "aws_subnet" "lh_aws_public_subnet" {
  vpc_id     = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "lh_public_subnet-${random_string.random_suffix.id}"
  }
}

# Create private subnet
resource "aws_subnet" "lh_aws_private_subnet" {
  vpc_id     = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.2.0/24"

  tags = {
    Name = "lh_private_subnet-${random_string.random_suffix.id}"
  }
}

# Create EIP for NATGW
resource "aws_eip" "lh_aws_eip_nat_gw" {
  vpc      = true

  tags = {
    Name = "lh_eip_nat_gw-${random_string.random_suffix.id}"
  }
}

# Create nat gateway
resource "aws_nat_gateway" "lh_aws_nat_gw" {
  depends_on = [
    aws_internet_gateway.lh_aws_igw,
    aws_eip.lh_aws_eip_nat_gw,
    aws_subnet.lh_aws_public_subnet,
    aws_subnet.lh_aws_private_subnet
  ]

  allocation_id = aws_eip.lh_aws_eip_nat_gw.id
  subnet_id     = aws_subnet.lh_aws_public_subnet.id

  tags = {
    Name = "lh_eip_nat_gw-${random_string.random_suffix.id}"
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
  }
}

# Create route table for private subnets
resource "aws_route_table" "lh_aws_private_rt" {
  depends_on = [
    aws_nat_gateway.lh_aws_nat_gw
  ]

  vpc_id = aws_vpc.lh_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_nat_gateway.lh_aws_nat_gw.id
  }

  tags = {
    Name = "lh_aws_private_rt-${random_string.random_suffix.id}"
  }
}

# Assciate public subnet to public route table
resource "aws_route_table_association" "lh_aws_public_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_aws_public_subnet,
    aws_route_table.lh_aws_public_rt
  ]

  subnet_id      = aws_subnet.lh_aws_public_subnet.id
  route_table_id = aws_route_table.lh_aws_public_rt.id
}

# Assciate private subnet to private route table
resource "aws_route_table_association" "lh_aws_private_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_aws_private_subnet,
    aws_route_table.lh_aws_private_rt
  ]

  subnet_id      = aws_subnet.lh_aws_private_subnet.id
  route_table_id = aws_route_table.lh_aws_private_rt.id
}

# Create AWS key pair
resource "aws_key_pair" "lh_aws_pair_key" {
  key_name   = format("%s_%s", "lh_aws_key_pair", "${random_string.random_suffix.id}")
  public_key = file(var.aws_ssh_public_key_file_path)
}

# Create cluster secret (used for k3s on arm64 only)
resource "random_password" "k3s_cluster_secret" {
  length = var.arch == "arm64" ? 64 : 0
  special = false
}


# Create controlplane instances
resource "aws_instance" "lh_aws_instance_controlplane" {
 depends_on = [
    aws_subnet.lh_aws_public_subnet,
  ]

  count = var.lh_aws_instance_count_controlplane

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_centos.id
  instance_type = var.lh_aws_instance_type_controlplane

  subnet_id = aws_subnet.lh_aws_public_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp_controlplane.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_controlplane
  }

  key_name = aws_key_pair.lh_aws_pair_key.key_name
  user_data = var.arch == "arm64" ? data.template_file.provision_arm64_server.rendered : file("${path.module}/user-data-scripts/provision_amd64.sh")

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete	= "true"
    Owner = "longhorn-infra"
  }
}

resource "aws_eip" "lh_aws_eip_controlplane" {
  count    = var.lh_aws_instance_count_controlplane
  vpc      = true
}

# Associate every EIP with controlplane instance
resource "aws_eip_association" "lh_aws_eip_assoc" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_eip.lh_aws_eip_controlplane
  ]

  count    = var.lh_aws_instance_count_controlplane

  instance_id   = element(aws_instance.lh_aws_instance_controlplane, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_controlplane, count.index).id
}

# Create worker instances
resource "aws_instance" "lh_aws_instance_worker" {
  depends_on = [
    aws_internet_gateway.lh_aws_igw,
    aws_subnet.lh_aws_private_subnet,
    aws_instance.lh_aws_instance_controlplane
  ]

  count = var.lh_aws_instance_count_worker

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_centos.id
  instance_type = var.lh_aws_instance_type_worker

  subnet_id = aws_subnet.lh_aws_private_subnet.id
  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp_worker.id
  ]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_worker
  }

  key_name = aws_key_pair.lh_aws_pair_key.key_name
  user_data = var.arch == "arm64" ? data.template_file.provision_arm64_agent.rendered : file("${path.module}/user-data-scripts/provision_amd64.sh")

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete	= "true"
    Owner = "longhorn-infra"
  }
}

# wait for docker to start on controlplane instances (for rke on amd64 only)
resource "null_resource" "wait_for_docker_start_controlplane" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_instance.lh_aws_instance_worker,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  count = var.lh_aws_instance_count_controlplane

  provisioner "remote-exec" {

    inline = var.arch == "amd64" ? ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"] : null

    connection {
      type     = "ssh"
      user     = "centos"
      host     = element(aws_eip.lh_aws_eip_controlplane, count.index).public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

# wait for docker to start on worker instances (for rke on amd64 only)
resource "null_resource" "wait_for_docker_start_worker" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_instance.lh_aws_instance_worker,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  count = var.lh_aws_instance_count_worker

  provisioner "remote-exec" {
    inline = var.arch == "amd64" ? ["until( systemctl is-active docker.service ); do echo \"waiting for docker to start \"; sleep 2; done"] : null

    connection {
      type     = "ssh"
      user     = "centos"
      host     = element(aws_instance.lh_aws_instance_worker, count.index).private_ip
      private_key = file(var.aws_ssh_private_key_file_path)
      timeout  = "10m"
      bastion_user     = "centos"
      bastion_host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      bastion_private_key = file(var.aws_ssh_private_key_file_path)
    }
  }
}

# Download KUBECONFIG file (for k3s arm64 only)
resource "null_resource" "rsync_kubeconfig_file" {
  depends_on = [
    aws_instance.lh_aws_instance_controlplane,
    aws_eip.lh_aws_eip_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  provisioner "remote-exec" {
    inline = var.arch == "arm64" ? ["until([ -f /etc/rancher/k3s/k3s.yaml ] && [ `sudo /usr/local/bin/kubectl get nodes --no-headers | grep -v \"NotReady\" | wc -l` -eq ${var.lh_aws_instance_count_worker} ]); do echo \"waiting for k3s cluster nodes to be running\"; sleep 2; done"] : null

    connection {
      type     = "ssh"
      user     = "centos"
      host     = aws_eip.lh_aws_eip_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = var.arch == "arm64" ? "rsync -aPvz --rsync-path=\"sudo rsync\" -e \"ssh -o StrictHostKeyChecking=no -l centos -i ${var.aws_ssh_private_key_file_path}\" ${aws_eip.lh_aws_eip_controlplane[0].public_ip}:/etc/rancher/k3s/k3s.yaml .  && sed -i 's#https://127.0.0.1:6443#https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:6443#' k3s.yaml"  : "echo \"amd64 arch.. skipping\""
  }
}
