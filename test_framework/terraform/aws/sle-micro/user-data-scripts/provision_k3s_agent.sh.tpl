#!/bin/bash

if [ -b "/dev/nvme1n1" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/nvme1n1
  sudo mkdir /opt/sda1
  sudo mount /dev/nvme1n1 /opt/sda1

  sudo mkdir /opt/sda1/local
  sudo mkdir /opt/local-path-provisioner
  sudo mount --bind /opt/sda1/local /opt/local-path-provisioner

  sudo mkdir /opt/sda1/longhorn
  sudo mkdir /var/lib/longhorn
  sudo mount --bind /opt/sda1/longhorn /var/lib/longhorn
elif [ -b "/dev/xvdh" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi

curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="agent --token ${k3s_cluster_secret}" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" sh -
sudo systemctl start k3s-agent
