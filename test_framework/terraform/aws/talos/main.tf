terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 4.0"
    }
    talos = {
      source = "siderolabs/talos"
      version = "= 0.9.0"
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
    volume_size = var.block_device_size_controlplane
  }

  tags = {
    Name = "${var.lh_aws_instance_name_controlplane}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_ebs_volume" "lh_aws_ssd_volume_v1" {

  count = var.lh_aws_instance_count_worker

  availability_zone = var.aws_availability_zone
  size              = var.block_device_size_worker
  type              = "gp2"

  tags = {
    Name = "lh-aws-ssd-volume-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_ebs_volume" "lh_aws_ssd_volume_v2" {

  count = var.lh_aws_instance_count_worker

  availability_zone = var.aws_availability_zone
  size              = var.block_device_size_worker
  type              = "gp2"

  tags = {
    Name = "lh-aws-ssd-volume-${count.index}-${random_string.random_suffix.id}"
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
    volume_size = var.block_device_size_worker
  }

  tags = {
    Name = "${var.lh_aws_instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_volume_attachment" "lh_aws_ssd_volume_v1_att_k3s" {

  count = var.lh_aws_instance_count_worker

  device_name  = "/dev/xvdb"
  volume_id    = aws_ebs_volume.lh_aws_ssd_volume_v1[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker[count.index].id
  force_detach = true
}

resource "aws_volume_attachment" "lh_aws_ssd_volume_v2_att_k3s" {

  count = var.lh_aws_instance_count_worker

  device_name  = "/dev/xvdh"
  volume_id    = aws_ebs_volume.lh_aws_ssd_volume_v2[count.index].id
  instance_id  = aws_instance.lh_aws_instance_worker[count.index].id
  force_detach = true
}

resource "talos_machine_secrets" "machine_secrets" {}

data "talos_machine_configuration" "controlplane" {

  depends_on = [ aws_instance.lh_aws_instance_controlplane ]

  cluster_name       = "lh-tests-cluster"
  cluster_endpoint   = "https://${aws_instance.lh_aws_instance_controlplane[0].public_ip}:6443"
  machine_type       = "controlplane"
  machine_secrets    = talos_machine_secrets.machine_secrets.machine_secrets
  docs               = false
  examples           = false
  kubernetes_version = "${var.k8s_distro_version}"
  config_patches = [
    file("${path.module}/talos-patch.yaml")
  ]
}

data "talos_machine_configuration" "worker" {

  depends_on = [ aws_instance.lh_aws_instance_controlplane ]

  cluster_name       = "lh-tests-cluster"
  cluster_endpoint   = "https://${aws_instance.lh_aws_instance_controlplane[0].public_ip}:6443"
  machine_type       = "worker"
  machine_secrets    = talos_machine_secrets.machine_secrets.machine_secrets
  docs               = false
  examples           = false
  kubernetes_version = "${var.k8s_distro_version}"
  config_patches = [
    file("${path.module}/talos-patch-worker.yaml")
  ]
}

resource "talos_machine_configuration_apply" "controlplane" {
  count = var.lh_aws_instance_count_controlplane

  client_configuration        = talos_machine_secrets.machine_secrets.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  endpoint                    = aws_instance.lh_aws_instance_controlplane[count.index].public_ip
  node                        = aws_instance.lh_aws_instance_controlplane[count.index].private_ip
}

resource "talos_machine_configuration_apply" "worker" {
  count = var.lh_aws_instance_count_worker

  client_configuration        = talos_machine_secrets.machine_secrets.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
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

resource "talos_cluster_kubeconfig" "this" {
  depends_on = [talos_machine_bootstrap.this]

  client_configuration = talos_machine_secrets.machine_secrets.client_configuration
  endpoint             = aws_instance.lh_aws_instance_controlplane.0.public_ip
  node                 = aws_instance.lh_aws_instance_controlplane.0.private_ip
}

resource "local_file" "kubeconfig" {
  content  = nonsensitive(talos_cluster_kubeconfig.this.kubeconfig_raw)
  filename = "kubeconfig"
}

data "talos_cluster_health" "this" {
  depends_on = [
    talos_machine_configuration_apply.controlplane,
    talos_machine_configuration_apply.worker,
    talos_cluster_kubeconfig.this
  ]

  client_configuration = talos_machine_secrets.machine_secrets.client_configuration
  endpoints            = aws_instance.lh_aws_instance_controlplane.*.public_ip
  control_plane_nodes  = aws_instance.lh_aws_instance_controlplane.*.private_ip
  worker_nodes         = aws_instance.lh_aws_instance_worker.*.private_ip
}

# Generate Talos Schematic and upload to Talos Factory
resource "null_resource" "upload_schematic" {
  depends_on = [
    data.talos_cluster_health.this,
    local_file.talosconfig
  ]

  provisioner "local-exec" {
    command = <<EOT
      if [ ! -f "${path.module}/longhorn-talos.yaml" ]; then
        echo "Error: longhorn-talos.yaml file not found"
        exit 1
      fi

      curl -X POST --data-binary @${path.module}/longhorn-talos.yaml https://factory.talos.dev/schematics > ${path.module}/schematic_response.json
    EOT
  }
}

# Extract schematic ID from uploaded response
data "local_file" "schematic_response" {
  depends_on = [null_resource.upload_schematic]
  filename   = "${path.module}/schematic_response.json"
}

locals {
  schematic_id = jsondecode(data.local_file.schematic_response.content).id
  talos_version = "v${var.os_distro_version}"
}

# Patch Talos cluster worker nodes to mount /var/mnt/longhorn
resource "null_resource" "patch_worker_nodes" {
  depends_on = [null_resource.upload_schematic]
  count = var.lh_aws_instance_count_worker

  provisioner "local-exec" {
    command = <<EOT
talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config \
  -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} get disks
talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config \
  --endpoints ${aws_instance.lh_aws_instance_controlplane[0].public_ip} \
  -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} \
  patch mc --patch @${path.module}/user-volumes-patch.yaml
while true; do
  if talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} get volumestatus u-longhorn &>/dev/null; then
    echo "Volume u-longhorn is now available on ${aws_instance.lh_aws_instance_worker[count.index].private_ip}"
    break
  fi
  sleep 1
done
while true; do
  if talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} get mountstatus u-longhorn &>/dev/null; then
    echo "Mount u-longhorn is now available on ${aws_instance.lh_aws_instance_worker[count.index].private_ip}"
    break
  fi
  sleep 1
done
EOT
  }
}

# Upgrade Talos cluster worker nodes using schematic ID
resource "null_resource" "upgrade_worker_nodes" {
  depends_on = [null_resource.patch_worker_nodes]
  count = var.lh_aws_instance_count_worker

  provisioner "local-exec" {
    command = <<EOT
      talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config \
        --endpoints ${aws_instance.lh_aws_instance_controlplane[0].public_ip} \
        -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} \
        upgrade --image factory.talos.dev/installer/${local.schematic_id}:${local.talos_version}
      echo "Print containers & extensions"
      talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config \
        -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} containers
      talosctl --talosconfig ${abspath(path.module)}/talos_k8s_config \
        -n ${aws_instance.lh_aws_instance_worker[count.index].private_ip} get extensions
    EOT
  }
}
