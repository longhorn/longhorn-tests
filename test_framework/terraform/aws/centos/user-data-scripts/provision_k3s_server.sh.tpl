#!/bin/bash

set -e

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
    sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
    sudo setenforce  0
fi

sudo yum update -y                                                              
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools jq
sudo systemctl -q enable iscsid                                                 
sudo systemctl start iscsid

until (curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server --node-taint "node-role.kubernetes.io/master=true:NoExecute" --node-taint "node-role.kubernetes.io/master=true:NoSchedule" --tls-san ${k3s_server_public_ip}" INSTALL_K3S_VERSION="${k3s_version}" K3S_CLUSTER_SECRET="${k3s_cluster_secret}" sh -); do
  echo 'k3s server did not install correctly'
  sleep 2
done

until (kubectl get pods -A | grep 'Running'); do
  echo 'Waiting for k3s startup'
  sleep 5
done
