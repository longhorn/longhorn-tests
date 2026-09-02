#!/bin/bash

set -e

sudo modprobe uio
sudo modprobe uio_pci_generic
sudo modprobe vfio_pci
sudo modprobe nvme-tcp
sudo modprobe dm_crypt
sudo touch /etc/modules-load.d/modules.conf
sudo sh -c "cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
nvme-tcp
dm_crypt
EOF"

sudo sh -c "echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages"
sudo sh -c "echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf"

if [[ "${extra_block_device}" != true ]]; then
  if [[ -b "/dev/nvme1n1" ]]; then
    sudo mkfs.ext4 -E nodiscard /dev/nvme1n1
    sudo mkdir -p /mnt/sda1
    sudo mount /dev/nvme1n1 /mnt/sda1

    sudo mkdir -p /mnt/sda1/local
    sudo mkdir -p /opt/local-path-provisioner
    sudo mount --bind /mnt/sda1/local /opt/local-path-provisioner

    sudo mkdir -p /mnt/sda1/longhorn
    sudo mkdir -p /var/lib/longhorn
    sudo mount --bind /mnt/sda1/longhorn /var/lib/longhorn
  elif [ -b "/dev/xvdh" ]; then
    sudo mkfs.ext4 -E nodiscard /dev/xvdh
    sudo mkdir -p /var/lib/longhorn
    sudo mount /dev/xvdh /var/lib/longhorn
  fi
fi

sudo mkdir -p /etc/rancher/k3s

sudo sh -c "cat > /etc/rancher/k3s/config.yaml <<EOF
server: ${k3s_server_url}
token: ${k3s_cluster_secret}
kubelet-arg:
  - cpu-manager-policy=none
  - reserved-cpus=0
EOF
"

curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="agent" INSTALL_K3S_VERSION="${k3s_version}" sh -
sudo systemctl start k3s-agent

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/suse/.ssh/authorized_keys
fi