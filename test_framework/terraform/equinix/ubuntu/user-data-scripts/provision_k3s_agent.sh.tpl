#!/bin/bash

set -e
set -x

apt-get update
apt-get install -y nfs-common

if [ -b "/dev/nvme1n1" ]; then
  mkfs.ext4 -E nodiscard /dev/nvme1n1
  mkdir /mnt/sda1
  mount /dev/nvme1n1 /mnt/sda1

  mkdir /mnt/sda1/local
  mkdir /opt/local-path-provisioner
  mount --bind /mnt/sda1/local /opt/local-path-provisioner

  mkdir /mnt/sda1/longhorn
  mkdir /var/lib/longhorn
  mount --bind /mnt/sda1/longhorn /var/lib/longhorn
fi

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent --token ${cluster_token}" K3S_URL="${server_url}" INSTALL_K3S_VERSION="${distro_version}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done