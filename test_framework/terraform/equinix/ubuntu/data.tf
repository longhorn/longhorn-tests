data "template_file" "provision_k8s_server" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_server.sh.tpl") : file("${path.module}/user-data-scripts/provision_rke2_server.sh.tpl")
  vars = {
    cluster_token = random_password.cluster_token.result
    server_public_ip = cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0)
    distro_version =  var.k8s_distro_version
  }
}

data "template_file" "provision_k8s_agent" {
  template = var.k8s_distro_name == "k3s" ? file("${path.module}/user-data-scripts/provision_k3s_agent.sh.tpl") : file("${path.module}/user-data-scripts/provision_rke2_agent.sh.tpl")
  vars = {
    cluster_token = random_password.cluster_token.result
    server_url = "https://${cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0)}:${var.k8s_distro_name == "k3s" ? "6443" : "9345"}"
    distro_version = var.k8s_distro_version
  }
}
