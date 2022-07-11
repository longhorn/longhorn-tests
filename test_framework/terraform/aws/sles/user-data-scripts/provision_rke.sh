#!/bin/bash

sudo zypper ref -y
sudo zypper install -y -t pattern devel_basis
sudo zypper install -y open-iscsi docker nfs-client
sudo usermod -aG docker ec2-user
sudo systemctl enable docker
sudo systemctl start docker
sudo systemctl -q enable iscsid
sudo systemctl start iscsid;

if [ -b "/dev/xvdh" ]; then
  mkfs.ext4 -E nodiscard /dev/xvdh
  mkdir /var/lib/longhorn
  mount /dev/xvdh /var/lib/longhorn
fi
