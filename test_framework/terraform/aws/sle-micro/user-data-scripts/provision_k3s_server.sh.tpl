#!/bin/bash

curl -sfL https://get.k3s.io | sudo INSTALL_K3S_EXEC="server --node-taint "node-role.kubernetes.io/control-plane:NoSchedule" --tls-san ${k3s_server_public_ip} --write-kubeconfig-mode 644 --token ${k3s_cluster_secret}" INSTALL_K3S_VERSION="${k3s_version}" sh -
sudo systemctl start k3s

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/suse/.ssh/authorized_keys
fi