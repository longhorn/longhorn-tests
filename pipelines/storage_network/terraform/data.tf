locals {
  aws_ami_sles_arch = var.arch == "amd64" ? "x86_64" : var.arch
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
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_server_public_ip = aws_eip.aws_eip[0].public_ip
    k3s_version =  var.k8s_distro_version
    thick_plugin = var.thick_plugin
  }
}

# Generate template file for k3s agent
data "template_file" "provision_k3s_agent" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_agent.sh.tpl") : null
  vars = {
    k3s_server_url = "https://${aws_eip.aws_eip[0].public_ip}:6443"
    k3s_cluster_secret = random_password.cluster_secret.result
    k3s_version =  var.k8s_distro_version
    thick_plugin = var.thick_plugin
  }
}

# Generate template file for flannel
data "template_file" "flannel" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/flannel.sh.tpl") : null
  vars = {
    N1 = aws_network_interface.instance_eth1[0].private_ip
    N2 = aws_network_interface.instance_eth1[1].private_ip
    N3 = aws_network_interface.instance_eth1[2].private_ip
    mtu = var.mtu
  }
}

# Generate template file for routes
data "template_file" "routes" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/routes.sh.tpl") : null
  vars = {
    N1 = aws_network_interface.instance_eth1[0].private_ip
    N2 = aws_network_interface.instance_eth1[1].private_ip
    N3 = aws_network_interface.instance_eth1[2].private_ip
  }
}
