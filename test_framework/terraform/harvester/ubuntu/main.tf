terraform {
  required_providers {
    rancher2 = {
      source  = "rancher/rancher2"
      version = "~> 4.4.0"
    }
  }
}

provider "rancher2" {
  api_url   = var.lab_url
  insecure  = true
  access_key = var.lab_access_key
  secret_key = var.lab_secret_key
}

resource "random_string" "random_suffix" {
  length           = 8
  special          = false
  lower            = true
  upper            = false
}

data "rancher2_cluster_v2" "hal-cluster" {
  name = "hal"
}

resource "rancher2_cloud_credential" "e2e-credential" {
  name = "e2e-credential-${random_string.random_suffix.id}"
  harvester_credential_config {
    cluster_id = data.rancher2_cluster_v2.hal-cluster.cluster_v1_id
    cluster_type = "imported"
    kubeconfig_content = data.rancher2_cluster_v2.hal-cluster.kube_config
  }
}

resource "rancher2_machine_config_v2" "e2e-machine-config-controlplane" {

  generate_name = "e2e-machine-config-controlplane-${random_string.random_suffix.id}"

  harvester_config {

    vm_namespace = "longhorn-qa"

    cpu_count = "4"
    memory_size = "8"

    disk_info = <<EOF
    {
        "disks": [{
            "imageName": "longhorn-qa/image-zrzpd",
            "size": ${var.block_device_size_controlplane},
            "bootOrder": 1
        }]
    }
    EOF

    network_info = <<EOF
    {
        "interfaces": [{
            "networkName": "longhorn-qa/vlan-2011"
        }]
    }
    EOF

    ssh_user = "ubuntu"

    user_data = <<EOF
#cloud-config
ssh_authorized_keys:
  - >-
    ${file(var.ssh_public_key_file_path)}
  - ${var.custom_ssh_public_key}
package_update: true
packages:
  - qemu-guest-agent
  - iptables
runcmd:
  - - systemctl
    - enable
    - '--now'
    - qemu-guest-agent.service
EOF
  }
}

resource "rancher2_machine_config_v2" "e2e-machine-config-worker" {

  generate_name = "e2e-machine-config-worker-${random_string.random_suffix.id}"

  harvester_config {

    vm_namespace = "longhorn-qa"

    cpu_count = "4"
    memory_size = "8"

    disk_info = <<EOF
    {
        "disks": [{
            "imageName": "longhorn-qa/image-zrzpd",
            "size": ${var.block_device_size_worker},
            "bootOrder": 1
        },
        {
            "storageClassName": "harvester-longhorn",
            "size": ${var.block_device_size_worker},
            "bootOrder": 2
        }]
    }
    EOF

    network_info = <<EOF
    {
        "interfaces": [{
            "networkName": "longhorn-qa/vlan-2011"
        }]
    }
    EOF

    ssh_user = "ubuntu"

    user_data = <<EOF
#cloud-config
ssh_authorized_keys:
  - >-
    ${file(var.ssh_public_key_file_path)}
  - ${var.custom_ssh_public_key}
package_update: true
packages:
  - qemu-guest-agent
  - iptables
  - cryptsetup
  - dmsetup
runcmd:
  - - systemctl
    - enable
    - '--now'
    - qemu-guest-agent.service
  - apt-get update
  - apt-get install -y linux-modules-extra-`uname -r`
  - systemctl stop multipathd.service
  - systemctl stop multipathd.socket
  - systemctl disable multipathd.service
  - systemctl disable multipathd.socket
  - modprobe uio
  - modprobe uio_pci_generic
  - modprobe vfio_pci
  - modprobe nvme-tcp
  - modprobe dm_crypt
  - touch /etc/modules-load.d/modules.conf
  - echo uio >> /etc/modules-load.d/modules.conf
  - echo uio_pci_generic >> /etc/modules-load.d/modules.conf
  - echo vfio_pci >> /etc/modules-load.d/modules.conf
  - echo nvme-tcp >> /etc/modules-load.d/modules.conf
  - echo dm_crypt >> /etc/modules-load.d/modules.conf
  - echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
  - echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf
EOF
  }
}

resource "rancher2_cluster_v2" "e2e-cluster" {

  name = "e2e-cluster-${random_string.random_suffix.id}"

  kubernetes_version = var.k8s_distro_version

  rke_config {
    machine_pools {
      name = "control-plane-pool"
      cloud_credential_secret_name = rancher2_cloud_credential.e2e-credential.id
      control_plane_role = true
      etcd_role = true
      worker_role = false
      quantity = 1
      machine_config {
        kind = rancher2_machine_config_v2.e2e-machine-config-controlplane.kind
        name = rancher2_machine_config_v2.e2e-machine-config-controlplane.name
      }
    }
    machine_pools {
      name = "worker-pool"
      cloud_credential_secret_name = rancher2_cloud_credential.e2e-credential.id
      control_plane_role = false
      etcd_role = false
      worker_role = true
      quantity = 3
      machine_config {
        kind = rancher2_machine_config_v2.e2e-machine-config-worker.kind
        name = rancher2_machine_config_v2.e2e-machine-config-worker.name
      }
    }
    machine_selector_config {
      config = <<EOF
        cloud-provider-name: ""
EOF
    }
    machine_global_config = <<EOF
cni: "calico"
disable-kube-proxy: false
etcd-expose-metrics: false
EOF
    upgrade_strategy {
      control_plane_concurrency = "10%"
      worker_concurrency = "10%"
    }
    etcd {
      snapshot_schedule_cron = "0 */5 * * *"
      snapshot_retention = 5
    }
    chart_values = ""
  }
}

output "kube_config" {
  value = rancher2_cluster_v2.e2e-cluster.kube_config
  sensitive = "true"
}

output "cluster_id" {
  value = data.rancher2_cluster_v2.hal-cluster.cluster_v1_id
}
