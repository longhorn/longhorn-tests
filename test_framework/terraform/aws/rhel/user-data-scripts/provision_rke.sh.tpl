#!/bin/bash

DOCKER_VERSION=20.10

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
	sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
	sudo setenforce  0
fi

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools
sudo systemctl -q enable iscsid
sudo systemctl start iscsid
sudo systemctl disable nm-cloud-setup.service nm-cloud-setup.timer

if [ -b "/dev/xvdh" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi

until (curl https://releases.rancher.com/install-docker/$${DOCKER_VERSION}.sh | sudo sh); do
  echo 'docker did not install correctly'
  sleep 2
done

sudo usermod -aG docker ec2-user
