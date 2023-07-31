#!/bin/bash

DOCKER_VERSION=20.10

sudo sed -i 's#^SELINUX=.*$#SELINUX='"${selinux_mode}"'#' /etc/selinux/config

if [[ ${selinux_mode} == "enforcing" ]] ; then
  sudo setenforce  1
elif [[  ${selinux_mode} == "permissive" ]]; then
  sudo setenforce  0
fi

sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf update -y
sudo dnf group install -y "Development Tools"
sudo dnf install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools docker-ce docker-ce-cli containerd.io

sudo systemctl start iscsid
sudo systemctl enable iscsid

sudo systemctl start docker
sudo systemctl enable docker

sudo usermod -aG docker rocky

if [ -b "/dev/xvdh" ]; then
  sudo mkfs.ext4 -E nodiscard /dev/xvdh
  sudo mkdir /var/lib/longhorn
  sudo mount /dev/xvdh /var/lib/longhorn
fi
