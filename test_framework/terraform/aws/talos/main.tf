terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
    talos = {
      source = "siderolabs/talos"
      version = ">= 0.4.0"
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
    Owner = var.resources_owner
  }
}

# Create security group
resource "aws_security_group" "lh_aws_secgrp" {
  name        = "lh_aws_secgrp"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.lh_aws_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    description = "Egress everywhere"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    description = "Ingress everywhere"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "lh_aws_sec_grp-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

# Create subnet
resource "aws_subnet" "lh_aws_subnet" {
  vpc_id     = aws_vpc.lh_aws_vpc.id
  availability_zone = var.aws_availability_zone
  cidr_block = "10.0.1.0/24"

  tags = {
    Name = "lh_subnet-${random_string.random_suffix.id}"
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

# Create route table for subnet
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
    Owner = var.resources_owner
  }
}

# Associate subnet to route table
resource "aws_route_table_association" "lh_aws_subnet_rt_association" {
  depends_on = [
    aws_subnet.lh_aws_subnet,
    aws_route_table.lh_aws_rt
  ]

  subnet_id      = aws_subnet.lh_aws_subnet.id
  route_table_id = aws_route_table.lh_aws_rt.id
}

resource "aws_instance" "lh_aws_instance_controlplane" {
  count = var.lh_aws_instance_count_controlplane

  ami           = data.aws_ami.talos.id
  instance_type = var.lh_aws_instance_type_controlplane

  subnet_id = aws_subnet.lh_aws_subnet.id
  associate_public_ip_address = true
  vpc_security_group_ids = [aws_security_group.lh_aws_secgrp.id]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_controlplane
  }

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_instance" "lh_aws_instance_worker" {
  count = var.lh_aws_instance_count_worker

  ami           = data.aws_ami.talos.id
  instance_type = var.lh_aws_instance_type_worker

  subnet_id = aws_subnet.lh_aws_subnet.id
  associate_public_ip_address = true
  vpc_security_group_ids = [aws_security_group.lh_aws_secgrp.id]

  root_block_device {
    delete_on_termination = true
    volume_size = var.lh_aws_instance_root_block_device_size_controlplane
  }

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "talos_machine_secrets" "machine_secrets" {}

data "talos_machine_configuration" "controlplane" {

  depends_on = [ aws_instance.lh_aws_instance_controlplane ]

  count = var.lh_aws_instance_count_controlplane

  cluster_name       = "lh-tests-cluster"
  cluster_endpoint   = "https://${aws_instance.lh_aws_instance_controlplane[0].public_ip}:6443"
  machine_type       = "controlplane"
  machine_secrets    = talos_machine_secrets.machine_secrets.machine_secrets
  kubernetes_version = var.k8s_distro_version
  talos_version      = "v${var.os_distro_version}"
  docs               = false
  examples           = false
  config_patches = [
    file("${path.module}/talos-patch.yaml")
  ]
}

data "talos_machine_configuration" "worker" {

  depends_on = [ aws_instance.lh_aws_instance_controlplane ]

  count = var.lh_aws_instance_count_worker

  cluster_name       = "lh-tests-cluster"
  cluster_endpoint   = "https://${aws_instance.lh_aws_instance_controlplane[0].public_ip}:6443"
  machine_type       = "worker"
  machine_secrets    = talos_machine_secrets.machine_secrets.machine_secrets
  kubernetes_version = var.k8s_distro_version
  talos_version      = "v${var.os_distro_version}"
  docs               = false
  examples           = false
  config_patches = [
    file("${path.module}/talos-patch.yaml")
  ]
}

resource "talos_machine_configuration_apply" "controlplane" {
  count = var.lh_aws_instance_count_controlplane

  client_configuration        = talos_machine_secrets.machine_secrets.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane[count.index].machine_configuration
  endpoint                    = aws_instance.lh_aws_instance_controlplane[count.index].public_ip
  node                        = aws_instance.lh_aws_instance_controlplane[count.index].private_ip
}

resource "talos_machine_configuration_apply" "worker" {
  count = var.lh_aws_instance_count_worker

  client_configuration        = talos_machine_secrets.machine_secrets.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker[count.index].machine_configuration
  endpoint                    = aws_instance.lh_aws_instance_worker[count.index].public_ip
  node                        = aws_instance.lh_aws_instance_worker[count.index].private_ip
}

resource "talos_machine_bootstrap" "this" {
  depends_on = [talos_machine_configuration_apply.controlplane]

  client_configuration = talos_machine_secrets.machine_secrets.client_configuration
  endpoint             = aws_instance.lh_aws_instance_controlplane[0].public_ip
  node                 = aws_instance.lh_aws_instance_controlplane[0].private_ip
}

data "talos_client_configuration" "this" {
  cluster_name         = "lh-tests-cluster"
  client_configuration = talos_machine_secrets.machine_secrets.client_configuration
  endpoints            = aws_instance.lh_aws_instance_controlplane[*].public_ip
}

resource "local_file" "talosconfig" {
  content  = nonsensitive(data.talos_client_configuration.this.talos_config)
  filename = "talos_k8s_config"
}

data "talos_cluster_kubeconfig" "this" {
  depends_on = [talos_machine_bootstrap.this]

  client_configuration = talos_machine_secrets.machine_secrets.client_configuration
  endpoint             = aws_instance.lh_aws_instance_controlplane[0].public_ip
  node                 = aws_instance.lh_aws_instance_controlplane.0.private_ip
}

resource "local_file" "kubeconfig" {
  content  = nonsensitive(data.talos_cluster_kubeconfig.this.kubeconfig_raw)
  filename = "kubeconfig"
}
