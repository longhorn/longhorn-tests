#!/bin/bash

set -e

sudo systemctl restart guestregister # Sometimes registration fails on first boot.
sudo zypper ref
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi nfs-client jq azure-cli
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --node-taint "node-role.kubernetes.io/master=true:NoExecute" --node-taint "node-role.kubernetes.io/master=true:NoSchedule" --tls-san ${k3s_server_public_ip} --write-kubeconfig-mode 644 --token ${k3s_cluster_secret}" INSTALL_K3S_VERSION="${k3s_version}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

RETRY=0
MAX_RETRY=180
until (kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for k3s startup'
  sleep 5
  if [ $RETRY -eq $MAX_RETRY ]; then
    break
  fi
  RETRY=$((RETRY+1))
done

if [[ -n "${custom_ssh_public_key}" ]]; then
  echo "${custom_ssh_public_key}" >> /home/ec2-user/.ssh/authorized_keys
fi