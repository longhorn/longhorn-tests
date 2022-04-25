# Query AWS for RHEL AMI
locals {
  aws_ami_rhel_arch = var.arch == "amd64" ? "x86_64" : var.arch
}

data "aws_ami" "aws_ami_rhel" {

  most_recent      = true
  owners           = [var.aws_ami_rhel_account_number]

  filter {
    name   = "name"
    values = ["RHEL-${var.os_distro_version}_HVM*${local.aws_ami_rhel_arch}-*"]
  }
}

# Generate template file for RKE
data "template_file" "provision_rke" {
  template = var.k8s_distro_name == "rke" ? file("${path.module}/user-data-scripts/provision_rke.sh.tpl") : null
  vars = {
    selinux_mode = var.selinux_mode
  }
}

# Generate template file for k3s server on k3s
data "template_file" "provision_k3s_server" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_server.sh.tpl") : null
  vars = {
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_server_public_ip = aws_eip.lh_aws_eip_controlplane[0].public_ip
    k3s_version =  var.k8s_distro_version
    selinux_mode = var.selinux_mode
  }
}

# Generate template file for k3s agent on k3s
data "template_file" "provision_k3s_agent" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_agent.sh.tpl") : null
  vars = {
    k3s_server_url = "https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:6443"
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_version =  var.k8s_distro_version
    selinux_mode = var.selinux_mode

  }
}

# Generate template file for rke2 server
data "template_file" "provision_rke2_server" {
  template = var.k8s_distro_name == "rke2" ? file("${path.module}/user-data-scripts/provision_rke2_server.sh.tpl") : null
  vars = {
    rke2_cluster_secret = random_password.cluster_secret.result
    rke2_server_public_ip = aws_eip.lh_aws_eip_controlplane[0].public_ip
    rke2_version =  var.k8s_distro_version
    selinux_mode = var.selinux_mode
  }
}

# Generate template file for rke2 agent
data "template_file" "provision_rke2_agent" {
  template = var.k8s_distro_name == "rke2" ? file("${path.module}/user-data-scripts/provision_rke2_agent.sh.tpl") : null
  vars = {
    rke2_server_url = "https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:9345"
    rke2_cluster_secret = random_password.cluster_secret.result
    rke2_version =  var.k8s_distro_version
    selinux_mode = var.selinux_mode
  }
}
