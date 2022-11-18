#!/bin/bash

set -e
set -x

ip addr add ${server_public_ip} dev lo

apt-get update
apt-get install -y nfs-common jq

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --node-taint "node-role.kubernetes.io/master=true:NoExecute" --node-taint "node-role.kubernetes.io/master=true:NoSchedule" --tls-san ${server_public_ip} --write-kubeconfig-mode 644 --token ${cluster_token}" INSTALL_K3S_VERSION="${distro_version}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

until (kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for k3s startup'
  sleep 5
done
