#!/bin/bash

sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
    setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
    setenforce  0
fi

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="agent" K3S_URL="${k3s_server_url}" INSTALL_K3S_VERSION="${k3s_version}" K3S_CLUSTER_SECRET="${k3s_cluster_secret}" sh -); do
  echo 'k3s agent did not install correctly'
  sleep 2
done
