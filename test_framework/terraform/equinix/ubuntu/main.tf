terraform {
  required_providers {
    equinix = {
      source = "equinix/equinix"
    }
  }
}

provider "equinix" {
  auth_token    = var.equinix_auth_token
}

resource "random_password" "cluster_token" {
  length  = 64
  special = false
}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

resource "equinix_metal_ssh_key" "ssh_key" {
  name       = "longhorn-benchmark-test-ssh-key-${random_string.random_suffix.id}"
  public_key = file(var.ssh_public_key_file_path)
}

resource "equinix_metal_reserved_ip_block" "reserved_public_ip" {
  project_id = var.equinix_project_id
  type       = "public_ipv4"
  metro      = var.metro
  quantity   = 1
}

resource "equinix_metal_device" "control_plane" {

  depends_on = [
    equinix_metal_ssh_key.ssh_key
  ]

  hostname         = "${var.instance_name_controlplane}-${random_string.random_suffix.id}"
  plan             = var.instance_type_controlplane
  metro            = var.metro
  operating_system = "ubuntu_${replace(var.os_distro_version, ".", "_")}"
  billing_cycle    = "hourly"
  project_id       = var.equinix_project_id

  user_data = data.template_file.provision_k8s_server.rendered
}

resource "equinix_metal_ip_attachment" "control_plane_address_assignment" {
  device_id = equinix_metal_device.control_plane.id
  # following expression will result to sth like "147.229.10.152/32"
  cidr_notation = join("/", [cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0), "32"])
}

resource "equinix_metal_device" "workers" {

  depends_on = [
    equinix_metal_ip_attachment.control_plane_address_assignment
  ]

  count = var.worker_count

  hostname         = "${var.instance_name_worker}-${count.index}-${random_string.random_suffix.id}"
  plan             = var.instance_type_worker
  metro            = var.metro
  operating_system = "ubuntu_${replace(var.os_distro_version, ".", "_")}"
  billing_cycle    = "hourly"
  project_id       = var.equinix_project_id

  user_data = data.template_file.provision_k8s_agent.rendered
}

resource "null_resource" "rsync_kubeconfig_file" {

  depends_on = [
    equinix_metal_ip_attachment.control_plane_address_assignment
  ]

  provisioner "remote-exec" {
    inline = [
      "cloud-init status --wait",
      "if [ \"`cloud-init status | grep error`\" ]; then cat /var/log/cloud-init-output.log; fi",
      "until([ -f /etc/rancher/${var.k8s_distro_name}/${var.k8s_distro_name}.yaml ] && [ `KUBECONFIG=/etc/rancher/${var.k8s_distro_name}/${var.k8s_distro_name}.yaml kubectl get node -o jsonpath='{.items[*].status.conditions}' | jq '.[] | select(.type  == \"Ready\").status' | grep -ci true` -eq $((1 + ${var.worker_count})) ]); do echo \"waiting for k8s cluster nodes to be running\"; sleep 2; done"
    ]

    connection {
      type     = "ssh"
      user     = "root"
      host     = cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0)
      private_key = file(var.ssh_private_key_file_path)
    }
  }

  provisioner "local-exec" {
    command = "rsync -aPvz --rsync-path=\"rsync\" -e \"ssh -o StrictHostKeyChecking=no -l root -i ${var.ssh_private_key_file_path}\" ${cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0)}:/etc/rancher/${var.k8s_distro_name}/${var.k8s_distro_name}.yaml . && sed -i 's#https://127.0.0.1:6443#https://${cidrhost(equinix_metal_reserved_ip_block.reserved_public_ip.cidr_notation, 0)}:6443#' ${var.k8s_distro_name}.yaml"
  }
}
