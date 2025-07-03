locals {
  aws_ami_sles_arch = var.arch == "amd64" ? "x86_64" : var.arch

  control_plane_ipv6 = aws_instance.lh_aws_instance_controlplane[0].ipv6_addresses[0]
  control_plane_ipv4 = aws_eip.lh_aws_eip_controlplane[0].public_ip

  k3s_server_url = var.network_stack == "ipv6" ? format("https://[%s]:6443", local.control_plane_ipv6) : format("https://%s:6443", local.control_plane_ipv4)

  rke2_server_url = var.network_stack == "ipv6" ? format("https://[%s]:9345", local.control_plane_ipv6) : format("https://%s:9345", local.control_plane_ipv4)
}

data "aws_ami" "aws_ami_sles" {
  most_recent      = true
  owners           = [var.aws_ami_sles_account_number]
  name_regex       = "^suse-sles-${var.os_distro_version}-v\\d+-hvm-ssd-${local.aws_ami_sles_arch}"
}

# Generate template file for k3s server
data "template_file" "provision_k3s_server" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_server.sh.tpl") : null
  vars = {
    network_stack = var.network_stack
    control_plane_ipv4 = local.control_plane_ipv4
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_version =  var.k8s_distro_version
    custom_ssh_public_key = var.custom_ssh_public_key
  }
}

# Generate template file for k3s agent
data "template_file" "provision_k3s_agent" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_agent.sh.tpl") : null
  vars = {
    network_stack = var.network_stack
    k3s_server_url = local.k3s_server_url
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_version =  var.k8s_distro_version
    custom_ssh_public_key = var.custom_ssh_public_key
    extra_block_device = var.extra_block_device
  }
}

# Generate template file for rke2 server
data "template_file" "provision_rke2_server" {
  template = var.k8s_distro_name == "rke2" ? file("${path.module}/user-data-scripts/provision_rke2_server.sh.tpl") : null
  vars = {
    network_stack = var.network_stack
    control_plane_ipv4 = local.control_plane_ipv4
    rke2_cluster_secret = random_password.cluster_secret.result
    rke2_version =  var.k8s_distro_version
    cis_hardening = var.cis_hardening
    custom_ssh_public_key = var.custom_ssh_public_key
  }
}

# Generate template file for rke2 agent
data "template_file" "provision_rke2_agent" {
  template = var.k8s_distro_name == "rke2" ? file("${path.module}/user-data-scripts/provision_rke2_agent.sh.tpl") : null
  vars = {
    network_stack = var.network_stack
    rke2_server_url = local.rke2_server_url
    rke2_cluster_secret = random_password.cluster_secret.result
    rke2_version =  var.k8s_distro_version
    cis_hardening = var.cis_hardening
    custom_ssh_public_key = var.custom_ssh_public_key
    extra_block_device = var.extra_block_device
  }
}
