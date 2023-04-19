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
exit $?
