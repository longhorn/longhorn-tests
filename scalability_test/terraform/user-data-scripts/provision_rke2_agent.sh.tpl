#!/bin/bash 

set -x

apt-get update
apt-get install -y nfs-common

until (curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="agent" INSTALL_RKE2_VERSION="${rke2_version}" sh -); do
  echo "fail to download rke2 version ${rke2_version}"
  sleep 2
done

systemctl enable rke2-agent.service

mkdir -p /etc/rancher/rke2/
touch /etc/rancher/rke2/config.yaml

echo "server: ${rke2_server_url}
token: ${rke2_cluster_secret}
node-label:
  - \"node-role.longhorn.io/worker=true\"
  " > /etc/rancher/rke2/config.yaml


systemctl start rke2-agent.service


mkfs.ext4 ${os_device_name}
mkdir /data
mount ${os_device_name} /data