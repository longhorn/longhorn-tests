#!/bin/bash 

set -x

apt-get update
apt-get install -y nfs-common

until (curl -sfL https://get.rke2.io | INSTALL_RKE2_VERSION="${rke2_version}" sh -); do
  echo "fail to download rke2 version ${rke2_version}"
  sleep 2
done

systemctl enable rke2-server.service

mkdir -p /etc/rancher/rke2/
touch /etc/rancher/rke2/config.yaml

echo "token: ${rke2_cluster_secret} 
tls-san:
  - ${rke2_server_public_ip}
node-taint:
  - \"CriticalAddonsOnly=true:NoExecute\"
  " > /etc/rancher/rke2/config.yaml


systemctl start rke2-server.service


until (/var/lib/rancher/rke2/bin/kubectl --kubeconfig=/etc/rancher/rke2/rke2.yaml get nodes | grep -w "$$HOSTNAME " | grep -w " Ready "); do
  echo "Waiting for rke2 server ($${HOSTNAME}) to startup"
  sleep 5
done
