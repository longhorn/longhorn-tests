# Query AWS for Ubuntu AMI
data "aws_ami" "aws_ami_ubuntu" {
  most_recent      = true
  owners           = [var.aws_ami_ubuntu_account_number]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu*${var.distro_version}-${var.arch}-server-*"]
  }
}

# Generate template file for k3s agent on arm64
data "template_file" "provision_arm64_server" {
  template = var.arch == "arm64" ? file("${path.module}/user-data-scripts/provision_arm64_server.sh.tpl") : null
  vars = {
    k3s_cluster_secret = random_password.k3s_cluster_secret.result
    k3s_server_public_ip = aws_eip.lh_aws_eip_controlplane[0].public_ip
    k3s_version =  var.k3s_version
  }
}

# Generate template file for k3s agent on arm64
data "template_file" "provision_arm64_agent" {
  template = var.arch == "arm64" ? file("${path.module}/user-data-scripts/provision_arm64_agent.sh.tpl") : null
  vars = {
    k3s_server_url = "https://${aws_eip.lh_aws_eip_controlplane[0].public_ip}:6443"
    k3s_cluster_secret = random_password.k3s_cluster_secret.result
    k3s_version =  var.k3s_version
  }
}

