#!/bin/bash

DOCKER_VERSION=20.10

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

until (curl https://releases.rancher.com/install-docker/$${DOCKER_VERSION}.sh | sudo sh); do
  echo 'docker did not install correctly'
  sleep 2
done

sudo usermod -aG docker ec2-user
