#!/bin/bash

set -e
set -x

apt-get update
apt-get install -y nfs-common cryptsetup dmsetup linux-modules-extra-`uname -r`

modprobe uio
modprobe uio_pci_generic
modprobe vfio_pci
modprobe nvme-tcp
modprobe dm_crypt
touch /etc/modules-load.d/modules.conf
cat > /etc/modules-load.d/modules.conf <<EOF
uio
uio_pci_generic
vfio_pci
nvme-tcp
dm_crypt
EOF

echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "vm.nr_hugepages=1024" >> /etc/sysctl.conf

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