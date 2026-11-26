# Private registry for airgap tests, living in the cluster's own VPC.
# It is only reachable from inside the VPC (443) and from the allowed CIDRs (22, for provisioning).
# The cluster nodes trust it through a self-signed CA written to their registries.yaml.

locals {
  registry_username = "registry_user"
  # a fixed address near the end of the subnet so the cert and the node user-data don't depend on the instance
  registry_ip = var.airgap ? cidrhost(aws_subnet.lh_aws_public_subnet.cidr_block, 250) : ""
}

data "aws_ami" "aws_ami_registry_ubuntu" {
  count       = var.airgap ? 1 : 0
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd*/ubuntu-*20.04-${var.arch}-server-*"]
  }
}

resource "random_string" "registry_password" {
  length  = 16
  special = false
  lower   = true
  upper   = false
}

# Self-signed CA and server certificate for the registry
resource "tls_private_key" "registry_ca" {
  count     = var.airgap ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_self_signed_cert" "registry_ca" {
  count                 = var.airgap ? 1 : 0
  private_key_pem       = tls_private_key.registry_ca[0].private_key_pem
  is_ca_certificate     = true
  validity_period_hours = 72
  allowed_uses          = ["cert_signing", "crl_signing"]

  subject {
    common_name = "lh-registry-ca-${random_string.random_suffix.id}"
  }
}

resource "tls_private_key" "registry" {
  count     = var.airgap ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_cert_request" "registry" {
  count           = var.airgap ? 1 : 0
  private_key_pem = tls_private_key.registry[0].private_key_pem
  ip_addresses    = [local.registry_ip]

  subject {
    common_name = local.registry_ip
  }
}

resource "tls_locally_signed_cert" "registry" {
  count                 = var.airgap ? 1 : 0
  cert_request_pem      = tls_cert_request.registry[0].cert_request_pem
  ca_private_key_pem    = tls_private_key.registry_ca[0].private_key_pem
  ca_cert_pem           = tls_self_signed_cert.registry_ca[0].cert_pem
  validity_period_hours = 72
  allowed_uses          = ["digital_signature", "key_encipherment", "server_auth"]
}

resource "aws_security_group" "lh_registry_aws_secgrp" {
  count       = var.airgap ? 1 : 0
  name        = "lh_registry_aws_secgrp_${random_string.random_suffix.id}"
  description = "Private registry for airgap tests"
  vpc_id      = aws_vpc.lh_aws_vpc.id

  ingress {
    description = "Allow SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = local.allowed_ipv4_cidrs
  }

  ingress {
    description = "Allow registry access from the cluster"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.lh_aws_vpc.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name  = "lh-registry-secgrp-${random_string.random_suffix.id}"
    Owner = var.resources_owner
  }
}

resource "aws_instance" "lh_registry_aws_instance" {
  count = var.airgap ? 1 : 0

  depends_on = [
    aws_route_table_association.lh_aws_public_subnet_rt_association,
  ]

  availability_zone           = var.aws_availability_zone
  ami                         = data.aws_ami.aws_ami_registry_ubuntu[0].id
  instance_type               = var.registry_aws_instance_type
  subnet_id                   = aws_subnet.lh_aws_public_subnet.id
  private_ip                  = local.registry_ip
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.lh_registry_aws_secgrp[0].id]
  key_name                    = aws_key_pair.lh_aws_pair_key.key_name

  root_block_device {
    delete_on_termination = true
    volume_size           = 40
  }

  tags = {
    Name        = "lh-registry-${random_string.random_suffix.id}"
    DoNotDelete = "true"
    Owner       = var.resources_owner
  }
}

resource "null_resource" "registry_post_setup" {
  count = var.airgap ? 1 : 0

  depends_on = [
    aws_instance.lh_registry_aws_instance
  ]

  connection {
    type        = "ssh"
    user        = "ubuntu"
    host        = aws_instance.lh_registry_aws_instance[0].public_ip
    private_key = file(var.aws_ssh_private_key_file_path)
  }

  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then cat /var/log/cloud-init-output.log; fi",
      "mkdir -p /tmp/registry-certs"
    ]
  }

  provisioner "file" {
    content     = tls_locally_signed_cert.registry[0].cert_pem
    destination = "/tmp/registry-certs/public.crt"
  }

  provisioner "file" {
    content     = tls_private_key.registry[0].private_key_pem
    destination = "/tmp/registry-certs/private.key"
  }

  provisioner "file" {
    content     = tls_self_signed_cert.registry_ca[0].cert_pem
    destination = "/tmp/registry-certs/ca.crt"
  }

  provisioner "file" {
    source      = "${path.module}/user-data-scripts/provision_registry_server.sh"
    destination = "/tmp/provision_registry_server.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/provision_registry_server.sh",
      "docker_hub_username=${var.docker_hub_username} docker_hub_password=${var.docker_hub_password} registry_username=${local.registry_username} registry_password=${random_string.registry_password.id} registry_url=${local.registry_ip} longhorn_version=${var.longhorn_version} /tmp/provision_registry_server.sh",
    ]
  }
}
