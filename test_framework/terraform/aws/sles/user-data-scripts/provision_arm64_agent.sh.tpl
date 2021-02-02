#!/bin/bash

sudo zypper update -y
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi docker
sudo usermod -aG docker ec2-user
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

until (curl -sfL https://get.k3s.io | K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" K3S_CLUSTER_SECRET="${k3s_cluster_secret}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done
