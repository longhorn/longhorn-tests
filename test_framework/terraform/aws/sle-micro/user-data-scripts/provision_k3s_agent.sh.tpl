#!/bin/bash

set -e

sudo modprobe uio
sudo modprobe uio_pci_generic
sudo modprobe nvme-tcp
sudo modprobe dm_crypt
sudo touch /etc/modules-load.d/modules.conf
sudo sh -c "cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
nvme-tcp
dm_crypt
EOF"

sudo sh -c "echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages"
sudo sh -c "echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf"

if [[ "${extra_block_device}" != true ]]; then
  if [[ -b "/dev/nvme1n1" ]]; then
    mkfs.ext4 -E nodiscard /dev/nvme1n1
    mkdir /mnt/sda1
    mount /dev/nvme1n1 /mnt/sda1

    mkdir /mnt/sda1/local
    mkdir /opt/local-path-provisioner
    mount --bind /mnt/sda1/local /opt/local-path-provisioner

    mkdir /mnt/sda1/longhorn
    mkdir /var/lib/longhorn
    mount --bind /mnt/sda1/longhorn /var/lib/longhorn
  elif [ -b "/dev/xvdh" ]; then
    mkfs.ext4 -E nodiscard /dev/xvdh
    mkdir /var/lib/longhorn
    mount /dev/xvdh /var/lib/longhorn
  fi
fi

curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="agent --token ${k3s_cluster_secret}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -
sudo systemctl start k3s-agent

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/suse/.ssh/authorized_keys
fi