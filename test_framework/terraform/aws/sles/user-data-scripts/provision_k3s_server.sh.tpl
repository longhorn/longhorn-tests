#!/bin/bash

sudo zypper ref -y
sudo zypper install -y -t pattern devel_basis jq
sudo zypper install -y open-iscsi docker
sudo usermod -aG docker ec2-user
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --tls-san ${k3s_server_public_ip}" INSTALL_K3S_VERSION="${k3s_version}" K3S_CLUSTER_SECRET="${k3s_cluster_secret}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

until (kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for k3s startup'
  sleep 5
done

