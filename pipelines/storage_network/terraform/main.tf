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
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

resource "random_password" "cluster_secret" {
  length = 64
  special = false
}

resource "aws_vpc" "aws_vpc" {
  cidr_block = "10.0.0.0/16"

  assign_generated_ipv6_cidr_block  = true
  enable_dns_support                = true
  enable_dns_hostnames              = true

  tags = {
    Name = "${var.aws_vpc_name}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_internet_gateway" "aws_igw" {
  vpc_id = aws_vpc.aws_vpc.id

  tags = {
    Name = "lh_igw-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_route_table" "aws_public_rt" {
  depends_on = [
    aws_internet_gateway.aws_igw,
  ]

  vpc_id = aws_vpc.aws_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.aws_igw.id
  }

  route {
    ipv6_cidr_block = "::/0"
    gateway_id      = aws_internet_gateway.aws_igw.id
  }

  tags = {
    Name = "lh_aws_public_rt-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_subnet" "aws_subnet_1" {
  vpc_id                          = aws_vpc.aws_vpc.id
  availability_zone               = "us-east-1c"
  cidr_block                      = "10.0.1.0/24"
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.aws_vpc.ipv6_cidr_block, 8, 0)
  assign_ipv6_address_on_creation = true

  tags = {
    Name = "lh_subnet_1-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_subnet" "aws_subnet_2" {
  vpc_id                          = aws_vpc.aws_vpc.id
  availability_zone               = "us-east-1c"
  cidr_block                      = "10.0.2.0/24"
  ipv6_cidr_block                 = cidrsubnet(aws_vpc.aws_vpc.ipv6_cidr_block, 8, 1)
  assign_ipv6_address_on_creation = true

  tags = {
    Name = "lh_subnet_2-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_route_table_association" "aws_subnet_1_rt_association" {
  depends_on = [
    aws_subnet.aws_subnet_1,
    aws_route_table.aws_public_rt
  ]

  subnet_id      = aws_subnet.aws_subnet_1.id
  route_table_id = aws_route_table.aws_public_rt.id
}

resource "aws_route_table_association" "aws_subnet_2_rt_association" {
  depends_on = [
    aws_subnet.aws_subnet_2,
    aws_route_table.aws_public_rt
  ]

  subnet_id      = aws_subnet.aws_subnet_2.id
  route_table_id = aws_route_table.aws_public_rt.id
}

resource "aws_security_group" "aws_secgrp" {
  name        = "lh_aws_secgrp"
  description = "Allow all inbound traffic"
  vpc_id      = aws_vpc.aws_vpc.id

  ingress {
    description = "Allow all ports"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow all ports over IPv6"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = {
    Name = "lh_aws_secgrp-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_key_pair" "aws_pair_key" {
  key_name   = format("%s_%s", "aws_key_pair", random_string.random_suffix.id)
  public_key = file(var.aws_ssh_public_key_file_path)
}

resource "aws_network_interface" "instance_eth0" {
  subnet_id   = aws_subnet.aws_subnet_1.id
  security_groups = [aws_security_group.aws_secgrp.id]
  ipv6_address_count = 1

  count = var.aws_instance_count

  tags = {
    Name = "instance_eth0-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_instance" "aws_instance" {
  depends_on = [
    aws_subnet.aws_subnet_1,
    aws_subnet.aws_subnet_2,
    aws_network_interface.instance_eth0
  ]

  ami           = data.aws_ami.aws_ami_sles.id
  instance_type = var.aws_instance_type

  count = var.aws_instance_count

  network_interface {
    network_interface_id = aws_network_interface.instance_eth0[count.index].id
    device_index         = 0
  }

  root_block_device {
    delete_on_termination = true
    volume_size = var.block_device_size_worker
  }

  key_name = aws_key_pair.aws_pair_key.key_name
  user_data = count.index == 0 ? data.template_file.provision_k3s_server.rendered : data.template_file.provision_k3s_agent.rendered

  tags = {
    Name = "${var.aws_instance_name}-${count.index}-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner = var.resources_owner
  }
}

resource "aws_network_interface" "instance_eth1" {
  depends_on = [
    aws_subnet.aws_subnet_1,
    aws_subnet.aws_subnet_2,
    aws_instance.aws_instance
  ]

  subnet_id   = aws_subnet.aws_subnet_2.id
  security_groups = [aws_security_group.aws_secgrp.id]
  ipv6_address_count = 1

  count = var.aws_instance_count

  attachment {
    instance     = aws_instance.aws_instance[count.index].id
    device_index = 1
  }

  tags = {
    Name = "instance_eth1-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_eip" "aws_eip" {
  vpc      = true

  count = var.aws_instance_count

  tags = {
    Name = "aws_eip-${count.index}-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_eip_association" "aws_eip_assoc" {
  depends_on = [
    aws_instance.aws_instance,
    aws_eip.aws_eip
  ]

  count = var.aws_instance_count

  network_interface_id    = aws_network_interface.instance_eth0[count.index].id
  allocation_id = aws_eip.aws_eip[count.index].id
}

resource "null_resource" "rsync_kubeconfig_file" {

  depends_on = [
    aws_instance.aws_instance,
    aws_eip.aws_eip,
    aws_eip_association.aws_eip_assoc
  ]

  provisioner "remote-exec" {

    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then sudo cat /var/log/cloud-init-output.log; fi",
      "RETRY=0; MAX_RETRY=450; until([ -f /etc/rancher/k3s/k3s.yaml ] && [ `sudo /usr/local/bin/kubectl get node -o jsonpath='{.items[*].status.conditions}'  | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq ${var.aws_instance_count} ]); do echo \"waiting for k3s cluster nodes to be running\"; sleep 2; if [ $RETRY -eq $MAX_RETRY ]; then break; fi; RETRY=$((RETRY+1)); done"
    ]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.aws_eip[0].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = <<EOT
    export K3S_SERVER_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "[${aws_instance.aws_instance[0].ipv6_addresses[0]}]" || echo ${aws_eip.aws_eip[0].public_ip}
    )
    export LOCAL_IP=$(
        [ "${var.network_stack}" = "ipv6" ] && echo "\[::1\]" || echo "127.0.0.1"
    )
    rsync -aPvz --rsync-path="sudo rsync" -e "ssh -o StrictHostKeyChecking=no -l ec2-user -i ${var.aws_ssh_private_key_file_path}" "${aws_eip.aws_eip[0].public_ip}:/etc/rancher/k3s/k3s.yaml" . && \
    sed -i "s#https://$LOCAL_IP:6443#https://$K3S_SERVER_IP:6443#" k3s.yaml
EOT
  }
}

# setup flannel
resource "null_resource" "cluster_setup_flannel" {
  count = var.aws_instance_count

  depends_on = [
    aws_instance.aws_instance,
    null_resource.rsync_kubeconfig_file
  ]

  provisioner "remote-exec" {

    inline = [data.template_file.flannel.rendered]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.aws_eip[count.index].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

}

# setup routes
resource "null_resource" "cluster_setup_routes" {
  count = var.aws_instance_count

  depends_on = [
    aws_instance.aws_instance,
    null_resource.cluster_setup_flannel
  ]

  provisioner "remote-exec" {

    inline = [data.template_file.routes.rendered]

    connection {
      type     = "ssh"
      user     = "ec2-user"
      host     = aws_eip.aws_eip[count.index].public_ip
      private_key = file(var.aws_ssh_private_key_file_path)
    }
  }

}