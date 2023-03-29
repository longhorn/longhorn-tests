#!/bin/bash

curl -sfL https://get.rke2.io | sudo INSTALL_RKE2_TYPE="server" INSTALL_RKE2_VERSION="${rke2_version}" sh -

sudo mkdir -p /etc/rancher/rke2

sudo tee -a /etc/rancher/rke2/config.yaml >/dev/null <<EOF
write-kubeconfig-mode: "0644"
token: ${rke2_cluster_secret}
tls-san:
  - ${rke2_server_public_ip}
node-taint:
  - "node-role.kubernetes.io/control-plane=true:NoSchedule"
EOF

sudo systemctl enable rke2-server.service
sudo systemctl start rke2-server.service
sudo ln -s /var/lib/rancher/rke2/bin/kubectl /usr/local/bin/kubectl