#!/bin/bash

apt-get update
apt-get install -y nfs-common jq


curl -sfL https://get.rke2.io | INSTALL_RKE2_TYPE="server" INSTALL_RKE2_VERSION="${rke2_version}" sh -

mkdir -p /etc/rancher/rke2

cat << EOF > /etc/rancher/rke2/config.yaml

write-kubeconfig-mode: "0644"
token: ${rke2_cluster_secret}
tls-san:
  - ${rke2_server_public_ip}
node-taint:
  - "node-role.kubernetes.io/control-plane:NoSchedule"
EOF

systemctl stop multipathd.socket
systemctl disable multipathd.socket
systemctl stop multipathd.service
systemctl disable multipathd.service
systemctl enable rke2-server.service
systemctl start rke2-server.service

until (KUBECONFIG=/etc/rancher/rke2/rke2.yaml /var/lib/rancher/rke2/bin/kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for rke2 startup'
  sleep 5
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ubuntu/.ssh/authorized_keys
fi
