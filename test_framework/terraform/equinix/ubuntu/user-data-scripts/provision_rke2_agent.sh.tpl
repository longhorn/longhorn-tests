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

RKE_SERVER_IP=`echo ${server_url} | sed 's#https://##' | awk -F ":" '{print $1}'`
RKE_SERVER_PORT=`echo ${server_url} | sed 's#https://##' | awk -F ":" '{print $2}'`

while ! nc -z $${RKE_SERVER_IP} $${RKE_SERVER_PORT}; do
  sleep 10 #
done

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${distro_version}" sh -

mkdir -p /etc/rancher/rke2

cat << EOF > /etc/rancher/rke2/config.yaml
server: ${server_url}
token: ${cluster_token}
EOF

systemctl enable rke2-agent.service
systemctl start rke2-agent.service
exit $?
