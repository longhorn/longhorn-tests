# Query AWS for Ubuntu AMI
data "aws_ami" "aws_ami_ubuntu" {
  most_recent = true
  owners      = [var.aws_ami_ubuntu_account_number]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu*${var.distro_version}-amd64-server-*"]
  }
}

data "template_file" "provision_rke2_first_server" {
  template = file("${path.module}/user-data-scripts/provision_rke2_first_server.sh.tpl")
  vars = {
    rke2_cluster_secret   = random_password.rke2_cluster_secret.result
    rke2_server_public_ip = aws_eip.lh_aws_eip_first_controlplane[0].public_ip
    rke2_version          = var.rke2_version
  }
}

data "template_file" "provision_rke2_additional_server" {
  template = file("${path.module}/user-data-scripts/provision_rke2_additional_server.sh.tpl")
  vars = {
    rke2_cluster_secret   = random_password.rke2_cluster_secret.result
    rke2_server_public_ip = aws_eip.lh_aws_eip_first_controlplane[0].public_ip
    rke2_version          = var.rke2_version
  }
}

# Generate template file for rke2 agent on arm64
data "template_file" "provision_rke2_agent" {
  template = file("${path.module}/user-data-scripts/provision_rke2_agent.sh.tpl")
  vars = {
    rke2_server_url     = "https://${aws_eip.lh_aws_eip_first_controlplane[0].public_ip}:9345"
    rke2_cluster_secret = random_password.rke2_cluster_secret.result
    rke2_version        = var.rke2_version
    os_device_name      = var.lh_aws_ebs_block_device_settings.os_device_name
  }
}

