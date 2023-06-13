#!/bin/bash

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
  sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
  sudo setenforce  0
fi

# Do not arbitrarily run "dnf update", as this will effectively move us up to the latest minor release.
sudo dnf group install -y "Development Tools"
sudo dnf install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools jq
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

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

until (KUBECONFIG=/etc/rancher/rke2/rke2.yaml /var/lib/rancher/rke2/bin/kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for rke2 startup'
  sleep 5
done
