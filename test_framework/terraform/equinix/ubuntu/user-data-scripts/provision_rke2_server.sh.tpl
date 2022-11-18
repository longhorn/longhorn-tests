#!/bin/bash

set -e
set -x

ip addr add ${server_public_ip} dev lo

apt-get update
apt-get install -y nfs-common jq

curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="server" INSTALL_RKE2_VERSION="${distro_version}" sh -

mkdir -p /etc/rancher/rke2

cat << EOF > /etc/rancher/rke2/config.yaml
write-kubeconfig-mode: "0644"
token: ${cluster_token}
tls-san:
  - ${server_public_ip}
node-taint:
  - "node-role.kubernetes.io/control-plane=true:NoSchedule"
EOF

systemctl enable rke2-server.service
systemctl start rke2-server.service

ln -s /var/lib/rancher/rke2/bin/kubectl /usr/local/bin/kubectl

until (KUBECONFIG=/etc/rancher/rke2/rke2.yaml kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for rke2 startup'
  sleep 5
done

