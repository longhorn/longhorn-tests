terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }
  required_version = ">= 0.14.9"
}

provider "aws" {
  region     = var.aws_region
  access_key = var.lh_aws_access_key
  secret_key = var.lh_aws_secret_key
}

# Create a non-default VPC
resource "aws_vpc" "lh_aws_vpc" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "lh_aws_vpc-${random_string.random_suffix.id}"
  }
}

# Create internet gateway
resource "aws_internet_gateway" "lh_aws_igw" {
  vpc_id = aws_vpc.lh_aws_vpc.id

  tags = {
    Name = "lh_igw-${random_string.random_suffix.id}"
  }
}

# Create a subnet
resource "aws_subnet" "lh_aws_subnet" {
  vpc_id            = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block        = "10.0.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name = "lh_aws_subnet-${random_string.random_suffix.id}"
  }
}

# Create a route table
resource "aws_route_table" "lh_aws_rt" {
  depends_on = [
    aws_internet_gateway.lh_aws_igw,
  ]

  vpc_id = aws_vpc.lh_aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.lh_aws_igw.id
  }

  tags = {
    Name = "lh_aws_rt-${random_string.random_suffix.id}"
  }
}

# Assciate the subnet with the route table
resource "aws_route_table_association" "lh_aws_subnet_rt_assoc" {
  depends_on = [
    aws_subnet.lh_aws_subnet,
    aws_route_table.lh_aws_rt
  ]

  subnet_id      = aws_subnet.lh_aws_subnet.id
  route_table_id = aws_route_table.lh_aws_rt.id
}

# Create security group for instances
resource "aws_security_group" "lh_aws_secgrp" {
  name        = "lh_aws_secgrp"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh_aws_vpc.id
  ingress {
    description = "Allow All Traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "lh_aws_secgrp"
  }
}

# Create AWS key pair
resource "aws_key_pair" "lh_aws_pair_key" {
  key_name   = format("%s_%s", "lh_aws_key_pair", md5(timestamp()))
  public_key = file(var.aws_ssh_public_key_file_path)
}

# Create cluster secret (used for rke2)
resource "random_password" "rke2_cluster_secret" {
  length  = 64
  special = false
}

# Create a random string suffix for instance names
resource "random_string" "random_suffix" {
  length  = 8
  special = false
  lower   = true
  upper   = false
}

# Create controlplane instances
resource "aws_instance" "lh_aws_instance_first_controlplane" {
  count = 1

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.lh_aws_instance_type_controlplane

  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp.id
  ]
  subnet_id = aws_subnet.lh_aws_subnet.id

  root_block_device {
    delete_on_termination = true
    volume_size           = var.lh_aws_instance_root_block_device_size_controlplane
  }

  key_name  = aws_key_pair.lh_aws_pair_key.key_name
  user_data = data.template_file.provision_rke2_first_server.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
  }
}

resource "aws_eip" "lh_aws_eip_first_controlplane" {
  count = 1
  vpc   = true
}

# Associate every EIP with the first controlplane
resource "aws_eip_association" "lh_aws_eip_assoc" {
  depends_on = [
    aws_instance.lh_aws_instance_first_controlplane,
    aws_eip.lh_aws_eip_first_controlplane
  ]

  count = 1

  instance_id   = element(aws_instance.lh_aws_instance_first_controlplane, count.index).id
  allocation_id = element(aws_eip.lh_aws_eip_first_controlplane, count.index).id
}

resource "null_resource" "wait_for_first_server_node" {
  depends_on = [
    aws_instance.lh_aws_instance_first_controlplane,
    aws_eip.lh_aws_eip_first_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  provisioner "remote-exec" {
    inline = ["until([ -f /etc/rancher/rke2/rke2.yaml ] && [ `sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig=/etc/rancher/rke2/rke2.yaml get nodes --no-headers | grep -v \"NotReady\" | wc -l` -eq 1 ]); do echo \"waiting for the first rke2 server to be running\"; sleep 2; done"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_eip.lh_aws_eip_first_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = "echo first rke2 server becomes running "
  }
}


resource "aws_instance" "lh_aws_instance_additional_controlplane" {
  depends_on = [
    null_resource.wait_for_first_server_node
  ]
  count = var.lh_aws_instance_count_controlplane > 1 ? var.lh_aws_instance_count_controlplane - 1 : 0

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.lh_aws_instance_type_controlplane

  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp.id
  ]
  subnet_id = aws_subnet.lh_aws_subnet.id

  root_block_device {
    delete_on_termination = true
    volume_size           = var.lh_aws_instance_root_block_device_size_controlplane
  }

  key_name  = aws_key_pair.lh_aws_pair_key.key_name
  user_data = data.template_file.provision_rke2_additional_server.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index + 1}-${random_string.random_suffix.id}"
  }
}

# Create worker instances
resource "aws_instance" "lh_aws_instance_worker" {
  depends_on = [
    null_resource.wait_for_first_server_node
  ]

  count = var.lh_aws_instance_count_worker

  availability_zone = var.aws_availability_zone

  ami           = data.aws_ami.aws_ami_ubuntu.id
  instance_type = var.lh_aws_instance_type_worker

  vpc_security_group_ids = [
    aws_security_group.lh_aws_secgrp.id
  ]
  subnet_id = aws_subnet.lh_aws_subnet.id

  root_block_device {
    delete_on_termination = true
    volume_size           = var.lh_aws_instance_root_block_device_size_worker
  }

  dynamic "ebs_block_device" {
    for_each = var.lh_aws_create_ebs_block_device ? [1] : []
    content {
      device_name           = var.lh_aws_ebs_block_device_settings.device_name
      volume_size           = var.lh_aws_ebs_block_device_settings.volume_size
      delete_on_termination = var.lh_aws_ebs_block_device_settings.delete_on_termination
      volume_type = var.lh_aws_ebs_block_device_settings.volume_type
      iops = var.lh_aws_ebs_block_device_settings.iops
      throughput = var.lh_aws_ebs_block_device_settings.throughput
    }
  }

  key_name  = aws_key_pair.lh_aws_pair_key.key_name
  user_data = data.template_file.provision_rke2_agent.rendered

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
  }
}

# Download KUBECONFIG file (for rke2)
resource "null_resource" "rsync_kubeconfig_file" {
  depends_on = [
    aws_instance.lh_aws_instance_first_controlplane,
    aws_eip.lh_aws_eip_first_controlplane,
    aws_eip_association.lh_aws_eip_assoc
  ]

  provisioner "remote-exec" {
    inline = ["until([ -f /etc/rancher/rke2/rke2.yaml ] && [ `sudo /var/lib/rancher/rke2/bin/kubectl --kubeconfig=/etc/rancher/rke2/rke2.yaml get nodes --no-headers | grep -v \"NotReady\" | wc -l` -eq ${var.lh_aws_instance_count_worker + length(aws_instance.lh_aws_instance_additional_controlplane)} ]); do echo \"waiting for rke2 cluster nodes to be running\"; sleep 2; done"]

    connection {
      type        = "ssh"
      user        = "ubuntu"
      host        = aws_eip.lh_aws_eip_first_controlplane[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = "rsync -aPvz --rsync-path=\"sudo rsync\" -e \"ssh -o StrictHostKeyChecking=no -l ubuntu -i ${var.aws_ssh_private_key_file_path}\" ${aws_eip.lh_aws_eip_first_controlplane[0].public_ip}:/etc/rancher/rke2/rke2.yaml .  && sed -i '' -e 's#https://127.0.0.1:6443#https://${aws_eip.lh_aws_eip_first_controlplane[0].public_ip}:6443#' rke2.yaml"
  }
}
