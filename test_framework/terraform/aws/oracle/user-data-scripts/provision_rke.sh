#!/bin/bash

DOCKER_VERSION=20.10

sudo systemctl stop firewalld
sudo systemctl disable firewalld

sudo yum update -y
sudo yum group install -y "Development Tools"
sudo yum install -y iscsi-initiator-utils nfs-utils nfs4-acl-tools cryptsetup
sudo systemctl -q enable iscsid
sudo systemctl start iscsid

until (curl https://releases.rancher.com/install-docker/${DOCKER_VERSION}.sh | sudo sh); do
  echo 'docker did not install correctly'
  sleep 2
done

sudo usermod -aG docker ec2-user

if [ -b "/dev/xvdh" ]; then
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi
