#!/bin/bash

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

RKE_SERVER_IP=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $1}'`
RKE_SERVER_PORT=`echo ${rke2_server_url} | sed 's#https://##' | awk -F ":" '{print $2}'`

curl -sfL https://get.rke2.io | sudo INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${rke2_version}" sh -

sudo mkdir -p /etc/rancher/rke2

sudo tee -a /etc/rancher/rke2/config.yaml >/dev/null <<EOF
server: ${rke2_server_url}
token: ${rke2_cluster_secret}
EOF

sudo systemctl enable rke2-agent.service
sudo systemctl start rke2-agent.service

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/suse/.ssh/authorized_keys
fi

exit $?